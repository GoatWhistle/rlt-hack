#!/usr/bin/env bash
set -euo pipefail

revision=${1:?Pass the Git revision}
bundle=${2:?Pass the bundle directory}
scratch=$(mktemp -d)
export RLT_DEPLOY_ROOT="$scratch/app"
export RLT_ENV_FILE="$scratch/production.env"
export RLT_PROJECT_NAME="rlt-ci-${revision:0:12}"
mkdir -p "$scratch/data"
cat > "$RLT_ENV_FILE" <<EOF
WEB_BIND=127.0.0.1
WEB_PORT=8081
CLICKHOUSE_USER=rlt
CLICKHOUSE_PASSWORD=ci-synthetic-password
CLICKHOUSE_DATABASE=supplier_search
RLT_DATA_DIR=$scratch/data
SUPPLIER_DATASET_PROVIDER=false
EOF

compose() {
  RLT_IMAGE_TAG=$revision docker compose --project-name "$RLT_PROJECT_NAME" \
    --env-file "$RLT_ENV_FILE" \
    --file "$RLT_DEPLOY_ROOT/releases/$revision/docker-compose.yml" \
    --file "$RLT_DEPLOY_ROOT/releases/$revision/deploy/compose.production.yml" "$@"
}

cleanup() {
  compose logs --tail 60 frontend clickhouse || true
  compose down --volumes || true
}
trap cleanup EXIT
(
  cd "$bundle"
  bash activate.sh "$revision" 1
)
compose run --rm --no-deps migrate
curl --fail --silent --show-error http://127.0.0.1:8081/nginx-health
curl --fail --silent --show-error http://127.0.0.1:8081/ > "$scratch/index.html"
grep -q 'type="module"' "$scratch/index.html"
test -s "$RLT_DEPLOY_ROOT/current/backup-before.txt"
compose exec -T clickhouse clickhouse-client --user rlt --multiquery --query \
  'CREATE TABLE supplier_search.ci_guard (id UInt64) ENGINE = MergeTree ORDER BY id;
   INSERT INTO supplier_search.ci_guard VALUES (1);'

broken_revision=0000000000000000000000000000000000000001
broken_bundle="$scratch/broken-bundle"
mkdir -p "$broken_bundle"
docker build --build-arg "BASE=rlt/frontend:$revision" \
  --label "org.opencontainers.image.revision=$broken_revision" \
  --tag "rlt/frontend:$broken_revision" - <<'EOF'
ARG BASE
FROM ${BASE}
RUN sed -i 's/return 200 "ok"/return 503 "unhealthy"/' /etc/nginx/conf.d/default.conf
EOF
docker build --build-arg "BASE=rlt/backend:$revision" \
  --label "org.opencontainers.image.revision=$broken_revision" \
  --tag "rlt/backend:$broken_revision" - <<'EOF'
ARG BASE
FROM ${BASE}
EOF
docker save "rlt/frontend:$broken_revision" "rlt/backend:$broken_revision" \
  | gzip > "$broken_bundle/images.tar.gz"
cp "$bundle/release.tar.gz" "$bundle/activate.sh" "$broken_bundle/"
(
  cd "$broken_bundle"
  sha256sum images.tar.gz release.tar.gz activate.sh > SHA256SUMS
)
if (cd "$broken_bundle" && bash activate.sh "$broken_revision" 2); then
  echo "An unhealthy release was incorrectly accepted" >&2
  exit 1
fi
test "$(readlink -f "$RLT_DEPLOY_ROOT/current")" = "$RLT_DEPLOY_ROOT/releases/$revision"
curl --fail --silent --show-error http://127.0.0.1:8081/nginx-health
backup=$(cat "$RLT_DEPLOY_ROOT/releases/$broken_revision/backup-before.txt")
compose exec -T clickhouse clickhouse-client --user rlt --query \
  "RESTORE TABLE supplier_search.ci_guard AS supplier_search.ci_guard_restored FROM Disk('backups', '$backup')"
count=$(compose exec -T clickhouse clickhouse-client --user rlt --query \
  'SELECT count() FROM supplier_search.ci_guard_restored')
test "$count" = 1
count=$(compose exec -T clickhouse clickhouse-client --user rlt --query \
  'SELECT count() FROM supplier_search.ci_guard')
test "$count" = 1
echo "Containers, migrations, backup restore, failed-release rollback and HTTP passed"
