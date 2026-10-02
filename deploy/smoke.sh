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
  compose logs --tail 60 api frontend clickhouse || true
  compose down --volumes || true
}
trap cleanup EXIT
(
  cd "$bundle"
  bash activate.sh "$revision" 1
)
compose run --rm --no-deps migrate
api=http://127.0.0.1:8081/api
curl --fail --silent --show-error http://127.0.0.1:8081/nginx-health
curl --fail --silent --show-error "$api/health/live"
curl --fail --silent --show-error "$api/health/ready"
compose exec -T clickhouse clickhouse-client --user rlt --multiquery --query \
  "INSERT INTO supplier_search.suppliers (supplier_id, inn, name, region, website,
     identity_status, identity_evidence_url, version)
   VALUES ('5e1d0c2e-0000-4000-8000-000000000001', '7801234564', 'ООО «Смоук»', '78',
     'https://smoke.example.ru', 'verified', '', 1);
   INSERT INTO supplier_search.sources (source_id, name, base_url, source_type, supplier_id,
     ownership_status, ownership_evidence_url, provider_name, version)
   VALUES ('5e1d0c2e-0000-4000-8000-000000000002', 'Каталог смоук', 'https://smoke.example.ru/',
     'directory', NULL, 'unverified', '', 'smoke', 1);
   INSERT INTO supplier_search.offers (offer_id, source_id, external_id, supplier_id,
     seller_status, url, name, description, item_type, brand, article, source_category,
     okpd2_code, price, currency, unit, availability, supplier_role, content_hash,
     first_seen_at, last_seen_at, version)
   VALUES ('5e1d0c2e-0000-4000-8000-000000000003', '5e1d0c2e-0000-4000-8000-000000000002',
     'p1', '5e1d0c2e-0000-4000-8000-000000000001', 'verified',
     'https://smoke.example.ru/p/1', 'Бумага офисная А4', 'Бумага для принтера', 'goods', '',
     '', 'Бумага', '', 250, 'RUB', 'пачка', 'available', 'distributor', 'smoke',
     now64(3), now64(3), 1);"
created=$(curl --fail --silent --show-error --dump-header "$scratch/search.headers" \
  --request POST --header 'Content-Type: application/json' \
  --data '{"text":"бумага офисная"}' "$api/searches")
test "$(jq '.candidates | length' <<<"$created")" -ge 1
search_id=$(jq -r .searchId <<<"$created")
location=$(grep -i '^location:' "$scratch/search.headers" | tr -d '\r' | cut -d' ' -f2)
test "$location" = "/api/searches/$search_id"
test "$(curl --fail --silent --show-error "http://127.0.0.1:8081$location" | jq -r .searchId)" \
  = "$search_id"
supplier_id=$(jq -r '.candidates[0].id' <<<"$created")
curl --fail --silent --show-error "$api/suppliers/$supplier_id" > /dev/null
printf 'lot_id;procedure_name;customer_inn\n1001;Поставка бумаги офисной;7801234564\n1002;Поставка бумаги А4;\n' \
  > "$scratch/notices.csv"
jar="$scratch/session.cookies"
created_upload=$(curl --fail --silent --show-error --cookie-jar "$jar" --cookie "$jar" \
  --form "file=@$scratch/notices.csv;type=text/csv" "$api/uploads")
upload_id=$(jq -r .id <<<"$created_upload")
test "$(jq '.total == 2 and .rejected == 0 and (.counts | has("failed"))' <<<"$created_upload")" = true
for _ in $(seq 60); do
  progress=$(curl --fail --silent --show-error --cookie "$jar" "$api/uploads/$upload_id/summary")
  if [[ $(jq '.processed == .total' <<<"$progress") == true ]]; then break; fi
  sleep 1
done
test "$(jq '.processed == .total and .counts.failed == 0' <<<"$progress")" = true
test "$(jq '.counts.ready + .counts.needsCheck + .counts.noCandidates' <<<"$progress")" = 2
detail=$(curl --fail --silent --show-error --cookie "$jar" "$api/uploads/$upload_id")
test "$(jq '[.lots[].searchId | select(. != null)] | length' <<<"$detail")" -ge 1
lot=$(curl --fail --silent --show-error --cookie "$jar" "$api/uploads/$upload_id/lots/1001")
test "$(jq '.search.candidates | length' <<<"$lot")" -ge 1
test "$(jq -r '.search.query.origin' <<<"$lot")" = upload
test "$(jq -r '.search.query.context.customerInn' <<<"$lot")" = 7801234564
test "$(jq -r '.search.searchId == .lot.searchId' <<<"$lot")" = true
lot_search=$(jq -r .lot.searchId <<<"$lot")
test "$(curl --fail --silent --show-error "$api/searches/$lot_search" | jq -r .searchId)" \
  = "$lot_search"
exported=$(curl --fail --silent --show-error --cookie "$jar" --request POST \
  --header 'Content-Type: application/json' --data '{"lotIds":["1001","1002"]}' \
  "$api/uploads/$upload_id/results")
test "$(jq '.results | length' <<<"$exported")" = 2
foreign=$(curl --silent --output /dev/null --write-out '%{http_code}' "$api/uploads/$upload_id")
test "$foreign" = 404
recent=$(curl --fail --silent --show-error "$api/searches")
test "$(jq --arg id "$lot_search" '[.searches[].searchId] | index($id) == null' <<<"$recent")" = true
test "$(curl --silent --output /dev/null --write-out '%{http_code}' "$api/metrics")" = 404
curl --fail --silent --show-error http://127.0.0.1:8081/ > "$scratch/index.html"
grep -q 'type="module"' "$scratch/index.html"
headers=$(curl --fail --silent --show-error --head http://127.0.0.1:8081/)
grep -qi '^referrer-policy:' <<<"$headers"
grep -qi '^content-security-policy:' <<<"$headers"
if grep -qi '^server:.*[0-9]' <<<"$headers"; then exit 1; fi
codes=$(seq 30 | xargs -P 15 -I{} curl --silent --output /dev/null \
  --write-out '%{http_code}\n' --request POST --header 'Content-Type: application/json' \
  --data '{"text":"бумага офисная"}' "$api/searches")
grep -qx 429 <<<"$codes"
grep -qx 201 <<<"$codes"
if grep -q '^5' <<<"$codes"; then exit 1; fi
test "$(compose exec -T api id -u)" != 0
docs=$(curl --silent --output /dev/null --write-out '%{http_code}' \
  http://127.0.0.1:8081/api/openapi.json)
test "$docs" = 404
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
docker build --build-arg "BASE=rlt/backend-api:$revision" \
  --label "org.opencontainers.image.revision=$broken_revision" \
  --tag "rlt/backend-api:$broken_revision" - <<'EOF'
ARG BASE
FROM ${BASE}
EOF
docker save "rlt/frontend:$broken_revision" "rlt/backend:$broken_revision" \
  "rlt/backend-api:$broken_revision" | gzip > "$broken_bundle/images.tar.gz"
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
