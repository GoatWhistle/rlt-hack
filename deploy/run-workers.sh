#!/usr/bin/env bash
set -euo pipefail

directory=${1:-$(readlink -f /opt/rlt-hack/current)}
export RLT_IMAGE_TAG
RLT_IMAGE_TAG=$(basename "$directory")
override=${RLT_COMPOSE_OVERRIDE:-/etc/rlt-hack/compose.override.yml}
extra=()
if [[ -f $override ]]; then extra=(--file "$override"); fi
compose() {
  docker compose --project-name "${RLT_PROJECT_NAME:-rlt-hack}" \
    --env-file "${RLT_ENV_FILE:-/etc/rlt-hack/production.env}" \
    --file "$directory/docker-compose.yml" \
    --file "$directory/deploy/compose.production.yml" "${extra[@]}" \
    --profile ml --profile workers --profile search "$@"
}
compose up -d --no-deps --wait --wait-timeout 180 embedder
compose run --rm --no-deps embedding-worker index --max-batches 1
compose up -d --no-deps --wait --wait-timeout 120 embedding-worker
if grep -Eq '^RLT_RUN_SEARCH=true$' "${RLT_ENV_FILE:-/etc/rlt-hack/production.env}"; then
  compose run --rm --no-deps --entrypoint python \
    search-api -m src.controller.search.import_index /data/index
  compose run --rm --no-deps --entrypoint python \
    --volume "${RLT_HISTORY_DIR:-/root/rlt/ready-v1}:/data/history:ro" \
    search-api -m src.controller.search.import_history /data/history/procurement.duckdb /data/index
  compose up -d --no-deps --wait --wait-timeout 180 search-api
fi
