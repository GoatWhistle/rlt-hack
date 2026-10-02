#!/usr/bin/env bash
set -euo pipefail

host=51.250.72.225
login=${RLT_VM_LOGIN:-rlt}
branch=deploy
root=$(git rev-parse --show-toplevel)
cd "$root"
known_hosts="$root/deploy/vm_known_hosts"

if [[ $(git rev-parse --abbrev-ref HEAD) != "$branch" ]]; then
  echo "Deploy only from the $branch branch" >&2
  exit 1
fi
if ! git diff --quiet HEAD; then
  echo "Commit the changes before deploying" >&2
  exit 1
fi

revision=$(git rev-parse HEAD)
run_id=$(date -u +%Y%m%d%H%M%S)
build=/opt/rlt-hack/build/upload
incoming="/opt/rlt-hack/incoming/$revision"
options=(-o BatchMode=yes -o ConnectTimeout=15 -o StrictHostKeyChecking=yes
  -o "UserKnownHostsFile=$known_hosts")
target="$login@$host"

git archive --format=tar "$revision" docker-compose.yml deploy backend frontend contracts \
  | ssh "${options[@]}" "$target" \
    'sudo -u rlt-deploy bash -c "rm -rf /opt/rlt-hack/build/upload && mkdir -p /opt/rlt-hack/build/upload && tar -x -C /opt/rlt-hack/build/upload"'
{
  printf 'revision=%q run_id=%q build=%q incoming=%q\n' \
    "$revision" "$run_id" "$build" "$incoming"
  cat <<'REMOTE'
set -euo pipefail
cd "$build"
bash deploy/package.sh "$revision" "$incoming" </dev/null
cd "$incoming"
bash activate.sh "$revision" "$run_id" </dev/null
rm -rf "$build" "$incoming"
REMOTE
} | ssh "${options[@]}" "$target" 'sudo -u rlt-deploy bash -s'
echo "Revision $revision is active on $host"
