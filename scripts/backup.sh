#!/usr/bin/env bash
#
# backup.sh — ежедневный backup PostgreSQL БД JobMap
# Запуск: crontab 0 3 * * * /opt/jobmap/scripts/backup.sh
#
set -euo pipefail

# ── Конфигурация ──
BACKUP_DIR="${BACKUP_DIR:-/opt/jobmap/backups}"
DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-job_service}"
DB_USER="${DB_USER:-job_service}"
DB_PASSWORD="${DB_PASSWORD:-}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
COMPRESS_LEVEL=6
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# ── Инициализация ──
mkdir -p "$BACKUP_DIR"

# ── Пароль через переменную окружения ──
export PGPASSWORD="$DB_PASSWORD"

# ── Backup ──
BACKUP_FILE="${BACKUP_DIR}/db_${DB_NAME}_${TIMESTAMP}.sql.gz"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting backup of $DB_NAME..."
echo "  Host: $DB_HOST:$DB_PORT"
echo "  Output: $BACKUP_FILE"

if pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --format=custom \
    --compress=$COMPRESS_LEVEL \
    --verbose \
    --file="$BACKUP_FILE" 2>&1
then
    FILESIZE=$(stat -c%s "$BACKUP_FILE" 2>/dev/null || stat -f%z "$BACKUP_FILE" 2>/dev/null)
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✓ Backup complete: $(numfmt --to=iec $FILESIZE)"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✗ Backup FAILED!"
    rm -f "$BACKUP_FILE"
    exit 1
fi

# ── SQL dump (для restore через psql) ──
SQL_FILE="${BACKUP_DIR}/db_${DB_NAME}_${TIMESTAMP}.sql.gz"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Creating SQL dump for easy restore..."

if pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --no-owner \
    --no-acl \
    --compress=$COMPRESS_LEVEL \
    --file="$SQL_FILE" 2>&1
then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✓ SQL dump created"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⚠ SQL dump failed (non-critical)"
fi

# ── Очистка старых backup'ов ──
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cleaning backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "db_*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "db_*.dump.gz" -type f -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✓ Backup rotation complete"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] === Backup finished ==="

# ── Последние backup'ы ──
ls -lh "$BACKUP_DIR"/*.sql.gz 2>/dev/null | tail -5
