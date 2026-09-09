#!/bin/sh
set -e

echo "Waiting for database..."
python - <<'PY'
import os, time
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from django.db import connection
for i in range(60):
    try:
        connection.ensure_connection()
        print("Database ready")
        break
    except Exception as exc:
        print(f"DB not ready ({i+1}/60): {exc}")
        time.sleep(2)
else:
    raise SystemExit("Database never became ready")
PY

python manage.py migrate --noinput
python manage.py collectstatic --noinput
# Seed is idempotent; never block API boot if duplicates already exist
python manage.py seed_joyclub || echo "seed_joyclub skipped/failed (non-fatal)"
python manage.py ensure_superuser \
  --email "${DJANGO_SUPERUSER_EMAIL:-Ajit@accounts.dovix.ai}" \
  --username "${DJANGO_SUPERUSER_USERNAME:-Ajit}" \
  --password "${DJANGO_SUPERUSER_PASSWORD:-ajit@123}"
# Demo tree is OFF in production. Set ENABLE_DEMO_ASSOCIATE=1 only for staging/dev.
if [ "${ENABLE_DEMO_ASSOCIATE:-0}" = "1" ]; then
  python manage.py ensure_demo_associate || echo "ensure_demo_associate skipped/failed (non-fatal)"
else
  echo "Skipping ensure_demo_associate (set ENABLE_DEMO_ASSOCIATE=1 to enable)"
fi
python manage.py ensure_landing_page || echo "ensure_landing_page skipped/failed (non-fatal)"

exec "$@"
