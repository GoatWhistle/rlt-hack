#!/usr/bin/env bash
set -euo pipefail

revision=${1:?Pass the Git revision}
output=${2:?Pass the bundle directory}
[[ $revision =~ ^[0-9a-f]{40}$ ]] || exit 2
mkdir -p "$output"

docker build --label "org.opencontainers.image.revision=$revision" \
  --file deploy/frontend.Dockerfile --target runtime \
  --tag "rlt/frontend:$revision" .
docker build --label "org.opencontainers.image.revision=$revision" \
  --target job --tag "rlt/backend:$revision" backend
docker build --label "org.opencontainers.image.revision=$revision" \
  --target api --tag "rlt/backend-api:$revision" backend
docker save "rlt/frontend:$revision" "rlt/backend:$revision" "rlt/backend-api:$revision" \
  | gzip > "$output/images.tar.gz"
tar -czf "$output/release.tar.gz" docker-compose.yml deploy backend/migration
cp deploy/release.sh "$output/activate.sh"
(
  cd "$output"
  sha256sum images.tar.gz release.tar.gz activate.sh > SHA256SUMS
)
