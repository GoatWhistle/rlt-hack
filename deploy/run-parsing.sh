#!/usr/bin/env bash
set -Eeuo pipefail

base=${RLT_DEPLOY_ROOT:-/opt/rlt-hack}
directory=$(readlink -f "$base/current")
project=${RLT_PROJECT_NAME:-rlt-hack}
name="$project-parsing"

export RLT_IMAGE_TAG
RLT_IMAGE_TAG=$(basename "$directory")
override=${RLT_COMPOSE_OVERRIDE:-/etc/rlt-hack/compose.override.yml}
extra=()
if [[ -f $override ]]; then extra=(--file "$override"); fi
compose() {
  docker compose --project-name "$project" \
    --env-file "${RLT_ENV_FILE:-/etc/rlt-hack/production.env}" \
    --file "$directory/docker-compose.yml" \
    --file "$directory/deploy/compose.production.yml" "${extra[@]}" "$@"
}

if [[ -n $(docker ps --quiet --filter "name=^${name}$") ]]; then
  echo "Parsing is already running in container $name" >&2
  exit 1
fi
if [[ -n $(docker ps --quiet --filter "name=^${project}-parser-worker") ]]; then
  echo "parser-worker is running; stop it before a manual crawl" >&2
  exit 1
fi
docker rm --force "$name" >/dev/null 2>&1 || true
compose run --detach --rm --no-deps --name "$name" sync-job sync
echo "Parsing started in container $name (release $RLT_IMAGE_TAG)"
echo "Logs: docker logs --follow $name"
