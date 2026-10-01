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
echo "Containers, repeated migrations, database backup and HTTP passed"
