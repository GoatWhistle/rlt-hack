#!/usr/bin/env bash
set -Eeuo pipefail
umask 027

revision=${1:?Pass the Git revision}
run_id=${2:?Pass the workflow run identifier}
[[ $revision =~ ^[0-9a-f]{40}$ && $run_id =~ ^[0-9]+$ ]] || exit 2
base=${RLT_DEPLOY_ROOT:-/opt/rlt-hack}
env_file=${RLT_ENV_FILE:-/etc/rlt-hack/production.env}
project=${RLT_PROJECT_NAME:-rlt-hack}
bundle=$(pwd)
release="$base/releases/$revision"
previous=""
frontend_changed=false
workers_changed=false

start_workers() {
  if grep -Eq '^RLT_RUN_WORKERS=true$' "$env_file"; then
    bash "$1/deploy/run-workers.sh" "$1"
  fi
}

compose_at() {
  local directory=$1
  local override=${RLT_COMPOSE_OVERRIDE:-/etc/rlt-hack/compose.override.yml}
  local extra=()
  if [[ -f $override ]]; then extra=(--file "$override"); fi
  shift
  RLT_IMAGE_TAG=$(basename "$directory") docker compose \
    --project-name "$project" --env-file "$env_file" \
    --file "$directory/docker-compose.yml" \
    --file "$directory/deploy/compose.production.yml" "${extra[@]}" "$@"
}

query() {
  local username
  username=$(compose_at "$release" exec -T clickhouse printenv CLICKHOUSE_USER)
  compose_at "$release" exec -T clickhouse clickhouse-client --user "$username" --query "$1"
}

failed() {
  local status=$?
  trap - EXIT
  if (( status == 0 )); then return; fi
  if [[ $workers_changed == true ]]; then
    compose_at "$release" --profile workers --profile ml stop parser-worker embedding-worker || true
    if [[ -n $previous && -f $previous/deploy/run-workers.sh ]]; then
      start_workers "$previous" || echo "Worker rollback failed; inspect containers" >&2
    fi
  fi
  if [[ $frontend_changed == true && -n $previous ]]; then
    echo "Deployment failed; restoring frontend $(basename "$previous")" >&2
    if ! compose_at "$previous" up -d --no-deps --wait --wait-timeout 120 frontend; then
      echo "Automatic frontend rollback failed; inspect the containers" >&2
    fi
  fi
  echo "Deployment $revision failed. Database volumes and backups are preserved." >&2
  exit "$status"
}
trap failed EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP

test -r "$env_file"
mkdir -p "$base/releases"
exec 9>"$base/deploy.lock"
flock -w 300 9
sha256sum -c "$bundle/SHA256SUMS"
if [[ -L $base/current ]]; then
  previous=$(readlink -f "$base/current")
fi
if [[ $previous == "$release" ]]; then
  compose_at "$release" up -d --no-deps --wait --wait-timeout 180 api frontend
  start_workers "$release"
  echo "Release $revision is already active"
  exit 0
fi

available=$(df --output=avail -k "$base" | tail -n 1)
if (( available < 2097152 )); then
  echo "Deployment requires at least 2 GiB of free disk space" >&2
  exit 1
fi
if [[ ! -d $release ]]; then
  staging=$(mktemp -d "$base/releases/.staging-$revision.XXXXXX")
  tar -xzf "$bundle/release.tar.gz" --no-same-owner -C "$staging"
  mv "$staging" "$release"
fi
chmod 0644 "$release/deploy/clickhouse-backup.xml"
compose_at "$release" config --quiet
docker load --input "$bundle/images.tar.gz"
for component in frontend backend backend-api; do
  actual=$(docker image inspect "rlt/$component:$revision" \
    --format '{{index .Config.Labels "org.opencontainers.image.revision"}}')
  test "$actual" = "$revision"
done

compose_at "$release" up -d --no-deps --wait --wait-timeout 180 clickhouse
database=$(compose_at "$release" exec -T clickhouse printenv CLICKHOUSE_DB)
[[ $database =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]] || exit 2
backup="before_${revision}_${run_id}_$(date -u +%Y%m%dT%H%M%SZ).zip"
query "BACKUP DATABASE $database TO Disk('backups', '$backup')"
printf '%s\n' "$backup" > "$release/backup-before.txt"
if grep -Eq '^RLT_RUN_WORKERS=true$' "$env_file"; then
  workers_changed=true
  compose_at "$release" --profile workers --profile ml stop parser-worker embedding-worker
fi
compose_at "$release" run --rm --no-deps migrate

frontend_changed=true
compose_at "$release" up -d --no-deps --wait --wait-timeout 180 api frontend
compose_at "$release" exec -T frontend wget -qO- http://127.0.0.1:8080/ >/dev/null
start_workers "$release"
if [[ -n $previous ]]; then
  ln -sfn "$previous" "$base/previous.next"
  mv -Tf "$base/previous.next" "$base/previous"
fi
ln -sfn "$release" "$base/current.next"
mv -Tf "$base/current.next" "$base/current"
trap - EXIT
echo "Release $revision is healthy and active"
