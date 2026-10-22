#!/bin/bash
# Temporary isolated backend on 127.0.0.1:8002 bound to the casa_e2e clone only.
set -euo pipefail
D=/app/backups/e2e
cd /app/backend
[ -s "$D/jwt_secret" ] || { echo "secret absent"; exit 1; }
export DB_NAME=casa_e2e CASA_TEST_DB=casa_e2e PUBLIC_APP_URL=http://localhost:8002 STORAGE_DISABLED=1
export CERT_WATERMARK="CLONE E2E — sans valeur"
export ADMIN_EMAIL= ADMIN_PASSWORD= LEARNER_EMAIL= LEARNER_PASSWORD= EMERGENT_LLM_KEY= TIGRIS_ACCESS_KEY_ID= TIGRIS_SECRET_ACCESS_KEY=
JWT_SECRET="$(cat "$D/jwt_secret")"
export JWT_SECRET
umask 077
nohup setsid python3 -m uvicorn server:app --host 127.0.0.1 --port 8002 > "$D/backend_8002.log" 2>&1 &
echo $! > "$D/8002.pid"
echo "instance 8002 lancée (pid $(cat "$D/8002.pid"))"
