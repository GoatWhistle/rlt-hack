#!/usr/bin/env bash
set -euo pipefail

test "$(id -u)" = 0
directory=$(cd "$(dirname "$0")" && pwd)
configuration=/etc/caddy/Caddyfile
test -f "$configuration"
curl --fail --silent --show-error http://127.0.0.1:8081/nginx-health >/dev/null
exec 9>/run/lock/rlt-caddy.lock
flock -w 30 9
if grep -Eq '^rlt\.goatwhistle\.ru[[:space:]]*\{' "$configuration"; then
  echo "Domain already exists; inspect the existing block before changing it" >&2
  exit 1
fi
# Блок веб-интерфейса БД подключается с сервера: путь и доступ в репозиторий
# не попадают. Заглушка нужна, чтобы шаблон import совпал и до установки
# интерфейса — пустой каталог Caddy считает ошибкой.
install -d -m 755 /etc/caddy/rlt-admin.d
if ! compgen -G '/etc/caddy/rlt-admin.d/*.conf' >/dev/null; then
  printf '# Заполняет deploy/install-admin-ui.sh\n' > /etc/caddy/rlt-admin.d/00-placeholder.conf
fi
backup="$configuration.before-rlt-$(date -u +%Y%m%dT%H%M%SZ)"
candidate=$(mktemp /etc/caddy/.Caddyfile.rlt.XXXXXX)
trap 'rm -f "$candidate"' EXIT
cp -p "$configuration" "$backup"
cp -p "$configuration" "$candidate"
printf '\n' >> "$candidate"
cat "$directory/Caddyfile" >> "$candidate"
caddy validate --config "$candidate" --adapter caddyfile
mv -f "$candidate" "$configuration"
if ! systemctl reload caddy; then
  cp -p "$backup" "$configuration"
  systemctl reload caddy
  exit 1
fi
echo "Domain configured; previous Caddy configuration: $backup"
