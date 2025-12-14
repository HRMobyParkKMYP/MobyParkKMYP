#!/bin/sh
set -e

: "${FERNET_KEY:?FERNET_KEY is required}"
: "${API_HOST_IP:?API_HOST_IP is required}"
: "${API_HOST_PORT:?API_HOST_PORT is required}"

cat > /app/api/.env <<EOF
FERNET_KEY=${FERNET_KEY}
API_HOST_IP=${API_HOST_IP}
API_HOST_PORT=${API_HOST_PORT}
EOF

exec uvicorn server:app --host "${API_HOST_IP}" --port "${API_HOST_PORT}"