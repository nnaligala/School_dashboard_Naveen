#!/bin/bash
# Usage: restore_db.sh /path/to/backup.dump.gpg target_db_name
# Restore into a NEW database first to verify, then swap. Never restore over production blindly.
set -euo pipefail
FILE="$1"; TARGET="$2"
createdb "$TARGET"
gpg --batch --decrypt "$FILE" | pg_restore --no-owner --dbname="$TARGET"
psql -d "$TARGET" -tc "SELECT count(*) AS users FROM accounts_user;"
