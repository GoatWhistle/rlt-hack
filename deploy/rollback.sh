#!/usr/bin/env bash
set -euo pipefail

base=${RLT_DEPLOY_ROOT:-/opt/rlt-hack}
env_file=${RLT_ENV_FILE:-/etc/rlt-hack/production.env}
project=${RLT_PROJECT_NAME:-rlt-hack}
test -L "$base/previous"
exec 9>"$base/deploy.lock"
flock -w 300 9
previous=$(readlink -f "$base/previous")
current=$(readlink -f "$base/current")
RLT_IMAGE_TAG=$(basename "$previous") docker compose \
  --project-name "$project" --env-file "$env_file" \
  --file "$previous/docker-compose.yml" \
  --file "$previous/deploy/compose.production.yml" \
  up -d --no-deps --wait --wait-timeout 120 frontend
ln -sfn "$previous" "$base/current.next"
mv -Tf "$base/current.next" "$base/current"
ln -sfn "$current" "$base/previous.next"
mv -Tf "$base/previous.next" "$base/previous"
echo "Frontend restored to $(basename "$previous"); database was not restored"
