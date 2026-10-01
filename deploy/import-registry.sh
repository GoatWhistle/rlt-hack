#!/usr/bin/env bash
set -Eeuo pipefail
umask 027

base=${RLT_DEPLOY_ROOT:-/opt/rlt-hack}
directory=$(readlink -f "$base/current")
registry_dir=${RLT_MSP_DIR:-$base/msp}
page=https://www.nalog.gov.ru/opendata/7707329152-rsmp/
url=${1:-}
parallel=${MSP_DOWNLOAD_PARALLEL:-16}
chunk=$((32 * 1024 * 1024))

export RLT_IMAGE_TAG
RLT_IMAGE_TAG=$(basename "$directory")
override=${RLT_COMPOSE_OVERRIDE:-/etc/rlt-hack/compose.override.yml}
extra=()
if [[ -f $override ]]; then extra=(--file "$override"); fi
compose() {
  RLT_MSP_DIR=$registry_dir docker compose --project-name "${RLT_PROJECT_NAME:-rlt-hack}" \
    --env-file "${RLT_ENV_FILE:-/etc/rlt-hack/production.env}" \
    --file "$directory/docker-compose.yml" \
    --file "$directory/deploy/compose.production.yml" "${extra[@]}" "$@"
}

latest_url() {
  curl --fail --silent --show-error --location --max-time 60 "$page" |
    grep -oE 'https://file\.nalog\.ru/opendata/[^"]+/data-[0-9]{8}-[^"]+\.zip' |
    sort -u |
    awk -F'data-' '{ d = substr($2, 1, 8); print substr(d, 5, 4) substr(d, 3, 2) substr(d, 1, 2), $0 }' |
    sort | tail -n 1 | cut -d' ' -f2
}

fetch_part() {
  local start=$1 size=$2 url=$3 parts=$4 chunk=$5
  local end=$((start + chunk - 1))
  if ((end >= size)); then end=$((size - 1)); fi
  local part
  part=$parts/$(printf '%012d' "$start")
  local want=$((end - start + 1))
  for _ in $(seq 1 20); do
    if [[ -f $part && $(stat -c %s "$part") -eq $want ]]; then return 0; fi
    if curl --fail --silent --max-time 900 --range "$start-$end" --output "$part.tmp" "$url" &&
      [[ $(stat -c %s "$part.tmp") -eq $want ]]; then
      mv "$part.tmp" "$part"
    fi
  done
  echo "Range $start-$end of $url failed" >&2
  return 1
}
export -f fetch_part

if [[ -z $url ]]; then url=$(latest_url); fi
[[ $url =~ ^https://file\.nalog\.ru/opendata/7707329152-rsmp/[A-Za-z0-9._-]+\.zip$ ]] || {
  echo "Unexpected registry dump URL: '$url'" >&2
  exit 2
}
echo "Registry dump: $url"

mkdir -p "$registry_dir"
[[ -w $registry_dir ]] || {
  echo "$registry_dir is not writable by $(id -un); fix its owner once" >&2
  exit 2
}
size=$(curl --fail --silent --show-error --head --location --max-time 60 "$url" |
  awk 'tolower($1) == "content-length:" { value = $2 } END { gsub("\r", "", value); print value }')
[[ $size =~ ^[0-9]+$ ]] || {
  echo "Registry dump size is unknown" >&2
  exit 1
}
target=$registry_dir/rmsp.zip
name=$(basename "$url")
if [[ -f $target && -f $target.source && $(cat "$target.source") == "$name" &&
  $(stat -c %s "$target") -eq $size ]]; then
  echo "Dump $name is already downloaded"
else
  parts=$registry_dir/parts-${name%.zip}
  mkdir -p "$parts"
  offset=0
  offsets=()
  while ((offset < size)); do
    offsets+=("$offset")
    offset=$((offset + chunk))
  done
  printf '%s\n' "${offsets[@]}" |
    xargs -P "$parallel" -I{} bash -c 'fetch_part "$@"' _ {} "$size" "$url" "$parts" "$chunk"
  cat "$parts"/0* > "$target.next"
  [[ $(stat -c %s "$target.next") -eq $size ]] || {
    echo "Downloaded dump has a wrong size" >&2
    exit 1
  }
  mv -f "$target.next" "$target"
  printf '%s\n' "$name" > "$target.source"
  rm -rf "$parts"
fi

# ClickHouse поднимается и ожидается явно: импорт идёт с --no-deps, поэтому
# depends_on джобы не действует, и на остановленной базе команда падала на
# первой же записи с Connection refused.
compose up -d --no-deps --wait --wait-timeout 180 clickhouse
compose run --rm --no-deps sync-job registry-import
