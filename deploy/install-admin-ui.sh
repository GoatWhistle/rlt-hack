#!/usr/bin/env bash
# Выкладывает интерфейс ClickHouse на закрытый путь домена.
# Страницу отдаёт Caddy со диска, запросы API уходят в контейнер clickhouse-ui.
# Путь и доступ — серверные секреты, в репозитории их нет.
set -Eeuo pipefail

test "$(id -u)" = 0

bundle=${RLT_ADMIN_BUNDLE:-/opt/rlt-hack/admin-ui/ui/dist}
target=${RLT_ADMIN_ROOT:-/var/lib/caddy/rlt-admin-ui}
snippet=${RLT_ADMIN_SNIPPET:-/etc/caddy/rlt-admin.d/clickhouse-ui.conf}
upstream=${RLT_ADMIN_UPSTREAM:-127.0.0.1:13488}

path=${RLT_ADMIN_PATH:-$(cat /etc/rlt-hack/admin-path)}
path=$(printf '%s' "$path" | tr -d '[:space:]')
path=${path#/}
path=${path%/}
test -n "$path"
user=${RLT_ADMIN_USER:?Set RLT_ADMIN_USER}
hash=${RLT_ADMIN_HASH:?Set RLT_ADMIN_HASH (bcrypt, caddy hash-password)}

test -f "$bundle/index.html"
# Бандл собирается под конкретный префикс: иначе страница запросит ресурсы
# по чужому пути и останется пустой.
grep -q "/$path/" "$bundle/index.html"

install -d -o caddy -g caddy -m 755 "$target"
# Содержимое заменяется целиком, иначе останутся ресурсы прошлой сборки
# с другими хешами в именах.
rm -rf "${target:?}"/*
cp -a "$bundle/." "$target/"
chown -R caddy:caddy "$target"

install -d -m 755 "$(dirname "$snippet")"
umask 027
cat > "$snippet" <<CONF
redir /$path /$path/ 308
handle_path /$path/* {
	basicauth {
		$user $hash
	}
	@backend path /api/* /connect /health /mcp /mcp/* /oauth/* /.well-known/*
	handle @backend {
		reverse_proxy $upstream {
			header_up -Authorization
		}
	}
	handle {
		root * $target
		try_files {path} /index.html
		file_server
	}
}
CONF
chown root:caddy "$snippet"

caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
systemctl reload caddy
echo "Admin UI installed: $(find "$target" -type f | wc -l) files, snippet $snippet"
