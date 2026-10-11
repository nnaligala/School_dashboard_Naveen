#!/bin/bash
# Save as /usr/local/bin/naveens-backup-db.sh (chmod 700). Run nightly via cron/systemd timer as user postgres.
# Needs a GPG public key imported for BACKUP_GPG_RECIPIENT.
set -euo pipefail
BACKUP_DIR="${BACKUP_DIR:-/var/backups/naveens}"
DB_NAME="${DB_NAME:-naveens_school}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$BACKUP_DIR/${DB_NAME}-${STAMP}.dump.gpg"
mkdir -p "$BACKUP_DIR"; umask 077
pg_dump --format=custom "$DB_NAME" | gpg --batch --encrypt --recipient "$BACKUP_GPG_RECIPIENT" > "$OUT"
[ -s "$OUT" ] || { echo "backup is empty" >&2; exit 1; }
find "$BACKUP_DIR" -name "${DB_NAME}-*.dump.gpg" -mtime +"$RETENTION_DAYS" -delete
echo "ok $OUT"
