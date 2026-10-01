#!/usr/bin/env bash
set -euo pipefail
umask 077

public_key=${1:?Pass the deployment public key file}
test "$(id -u)" = 0
ssh-keygen -l -f "$public_key" >/dev/null
docker compose version >/dev/null
directory=$(cd "$(dirname "$0")" && pwd)
if ! id rlt-deploy >/dev/null 2>&1; then
  useradd --system --create-home --home-dir /var/lib/rlt-deploy \
    --shell /bin/bash rlt-deploy
fi
usermod -aG docker rlt-deploy
install -d -o rlt-deploy -g rlt-deploy -m 0750 \
  /opt/rlt-hack /opt/rlt-hack/incoming /opt/rlt-hack/releases /opt/rlt-hack/data
install -d -o rlt-deploy -g rlt-deploy -m 0700 /var/lib/rlt-deploy/.ssh
authorized=/var/lib/rlt-deploy/.ssh/authorized_keys
touch "$authorized"
key="restrict $(cat "$public_key")"
if ! grep -Fqx "$key" "$authorized"; then
  printf '%s\n' "$key" >> "$authorized"
fi
chown rlt-deploy:rlt-deploy "$authorized"
chmod 0600 "$authorized"
install -d -o root -g rlt-deploy -m 0750 /etc/rlt-hack
if [[ ! -f /etc/rlt-hack/production.env ]]; then
  database_password=$(openssl rand -hex 32)
  sed "s/replace-with-a-generated-password/$database_password/" \
    "$directory/production.env.example" > /etc/rlt-hack/production.env
fi
chown root:rlt-deploy /etc/rlt-hack/production.env
chmod 0640 /etc/rlt-hack/production.env
echo "Deployment user and directories are ready"
