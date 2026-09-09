#!/usr/bin/env bash
# Isolated ROI-on-ROI smoke test — separate SQLite DB, no production impact.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$ROOT/backend"
OUT="$ROOT/scripts/roi-smoke-screens"
DB="$BACKEND/smoke_roi.sqlite3"
API_PORT="${SMOKE_API_PORT:-8011}"
WEB_PORT="${SMOKE_WEB_PORT:-$(python3 -c "import socket;s=socket.socket();s.bind(('',0));print(s.getsockname()[1]);s.close()")}"
export DATABASE_URL="sqlite:///$DB"
export VITE_API_URL="http://127.0.0.1:${API_PORT}/api/v1"
export CORS_ALLOWED_ORIGINS="http://127.0.0.1:${WEB_PORT},http://localhost:${WEB_PORT}"

mkdir -p "$OUT"
rm -f "$DB"

echo "==> Isolated DB: $DB"
cd "$BACKEND"
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py seed_roi_smoke --json 2>/dev/null | python3 -c "import sys; t=sys.stdin.read(); i=t.find('{'); sys.stdout.write(t[i:] if i>=0 else t)" > "$OUT/verification.json"

echo "==> Starting API on :$API_PORT"
.venv/bin/python manage.py runserver "127.0.0.1:${API_PORT}" --noreload &
API_PID=$!
for i in $(seq 1 30); do
  curl -sf "http://127.0.0.1:${API_PORT}/api/v1/app/latest/" >/dev/null 2>&1 && break
  sleep 1
done

echo "==> Starting frontend on :$WEB_PORT"
cd "$ROOT"
VITE_API_URL="$VITE_API_URL" npm run dev -- --host 127.0.0.1 --port "$WEB_PORT" --strictPort >"$OUT/vite.log" 2>&1 &
WEB_PID=$!
for i in $(seq 1 90); do
  if curl -sf "http://127.0.0.1:${WEB_PORT}/" >/dev/null 2>&1; then
    break
  fi
  if ! kill -0 "$WEB_PID" 2>/dev/null; then
    echo "Vite failed to start:" >&2
    tail -20 "$OUT/vite.log" >&2 || true
    exit 1
  fi
  sleep 2
done
if ! curl -sf "http://127.0.0.1:${WEB_PORT}/" >/dev/null 2>&1; then
  echo "Frontend not ready on :$WEB_PORT" >&2
  tail -20 "$OUT/vite.log" >&2 || true
  exit 1
fi
sleep 2

cleanup() {
  kill "$WEB_PID" 2>/dev/null || true
  kill "$API_PID" 2>/dev/null || true
  cd "$BACKEND"
  .venv/bin/python manage.py seed_roi_smoke --purge >/dev/null 2>&1 || true
  rm -f "$DB"
}
trap cleanup EXIT

echo "==> Playwright smoke + screenshots"
node "$ROOT/scripts/roi_on_roi_smoke_playwright.mjs" \
  --base "http://127.0.0.1:${WEB_PORT}" \
  --out "$OUT" \
  --report "$OUT/verification.json"

echo ""
echo "Done. Screenshots → $OUT"
ls -la "$OUT"/*.png 2>/dev/null || true
