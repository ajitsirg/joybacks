#!/usr/bin/env bash
# Daily PostgreSQL backup for JoyClub Associate.
# Writes into /opt/joyclub/backups (same project folder). Never deletes prior backups.
set -euo pipefail

REMOTE_DIR="${JOYCLUB_REMOTE_DIR:-/opt/joyclub}"
BACKUP_DIR="${JOYCLUB_BACKUP_DIR:-${REMOTE_DIR}/backups}"
COMPOSE_FILE="${REMOTE_DIR}/docker-compose.prod.yml"
ENV_FILE="${REMOTE_DIR}/.env.production"
STAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${BACKUP_DIR}/backup.log"

mkdir -p "${BACKUP_DIR}"

log() {
  echo "[$(date -Iseconds)] $*" | tee -a "${LOG_FILE}"
}

if [[ ! -f "${COMPOSE_FILE}" || ! -f "${ENV_FILE}" ]]; then
  log "ERROR: missing compose or env at ${REMOTE_DIR}"
  exit 1
fi

# shellcheck disable=SC1090
set -a
# shellcheck source=/dev/null
source <(grep -E '^(POSTGRES_DB|POSTGRES_USER|POSTGRES_PASSWORD)=' "${ENV_FILE}" | sed 's/\r$//')
set +a

DB_NAME="${POSTGRES_DB:-joyclub}"
DB_USER="${POSTGRES_USER:-joyclub}"
DUMP_CUSTOM="${BACKUP_DIR}/joyclub_${STAMP}.dump"
DUMP_SQL="${BACKUP_DIR}/joyclub_${STAMP}.sql.gz"

log "Starting backup → ${BACKUP_DIR}"

cd "${REMOTE_DIR}"

docker compose -f docker-compose.prod.yml --env-file .env.production exec -T db \
  pg_dump -U "${DB_USER}" -d "${DB_NAME}" -Fc \
  > "${DUMP_CUSTOM}"

docker compose -f docker-compose.prod.yml --env-file .env.production exec -T db \
  pg_dump -U "${DB_USER}" -d "${DB_NAME}" --no-owner --no-acl \
  | gzip -c > "${DUMP_SQL}"

if [[ ! -s "${DUMP_CUSTOM}" || ! -s "${DUMP_SQL}" ]]; then
  log "ERROR: backup file empty"
  exit 1
fi

SIZE_C="$(du -h "${DUMP_CUSTOM}" | awk '{print $1}')"
SIZE_S="$(du -h "${DUMP_SQL}" | awk '{print $1}')"
log "OK custom=${DUMP_CUSTOM} (${SIZE_C}) sql=${DUMP_SQL} (${SIZE_S})"
log "Retention: keep ALL backups (no automatic delete)"
