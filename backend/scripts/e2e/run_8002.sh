#!/bin/bash
# Temporary isolated backend on 127.0.0.1:8002 bound to a dedicated test database only (never the preproduction one).
set -euo pipefail
D=/app/backups/e2e
DB="${1:-casa_e2e}"
cd /app/backend
PREPROD=$(grep '^DB_NAME=' .env | cut -d= -f2- | tr -d '"')
[ "$DB" != "$PREPROD" ] || { echo "refusé : base de préproduction"; exit 1; }
[[ "$DB" == casa_e2e* ]] || { echo "refusé : la base doit commencer par casa_e2e"; exit 1; }
[ -s "$D/jwt_secret" ] || { echo "secret absent"; exit 1; }
export DB_NAME="$DB" CASA_TEST_DB="$DB" PUBLIC_APP_URL=http://localhost:8002 STORAGE_DISABLED=1 CORS_ORIGINS=http://localhost:3101
export CERT_WATERMARK="CLONE E2E — sans valeur"
export ADMIN_EMAIL= ADMIN_PASSWORD= LEARNER_EMAIL= LEARNER_PASSWORD= EMERGENT_LLM_KEY= TIGRIS_ACCESS_KEY_ID= TIGRIS_SECRET_ACCESS_KEY=
if [ -s "$D/admin_password" ]; then
  ADMIN_EMAIL=qa-e2e-admin@example.com
  ADMIN_PASSWORD="$(cat "$D/admin_password")"
fi
JWT_SECRET="$(cat "$D/jwt_secret")"
export JWT_SECRET
umask 077
nohup setsid python3 -m uvicorn server:app --host 127.0.0.1 --port 8002 > "$D/backend_8002.log" 2>&1 &
echo $! > "$D/8002.pid"
echo "instance 8002 lancée sur $DB (pid $(cat "$D/8002.pid"))"
