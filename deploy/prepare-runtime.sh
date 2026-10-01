#!/usr/bin/env bash
set -euo pipefail
umask 077

test "$(id -u)" = 0
directory=$(cd "$(dirname "$0")" && pwd)
install -d -m 0750 /opt/rlt-hack/data /opt/rlt-hack/runtime /etc/rlt-hack
if [[ ! -f /etc/rlt-hack/production.env ]]; then
  database_password=$(openssl rand -hex 32)
  sed "s/replace-with-a-generated-password/$database_password/" \
    "$directory/production.env.example" > /etc/rlt-hack/production.env
  chmod 0600 /etc/rlt-hack/production.env
fi
echo "Runtime directories and configuration are ready; SSH access was not changed"
