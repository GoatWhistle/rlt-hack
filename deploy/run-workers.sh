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
    --profile ml --profile workers "$@"
}
compose up -d --no-deps --wait --wait-timeout 180 embedder
compose run --rm --no-deps embedding-worker index --max-batches 1
compose up -d --no-deps --wait --wait-timeout 120 parser-worker embedding-worker
