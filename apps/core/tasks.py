from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import connection
from django.utils import timezone

from .models import AuditLog


@shared_task(name="apps.core.tasks.purge_old_audit_logs")
def purge_old_audit_logs():
    """Idempotent retention job. AuditLog.delete() is blocked per-row, so use a raw queryset delete."""
    cutoff = timezone.now() - timedelta(days=settings.AUDIT_RETENTION_DAYS)
    table = AuditLog._meta.db_table
    with connection.cursor() as cur:
        cur.execute(f"DELETE FROM {table} WHERE created_at < %s", [cutoff])  # noqa: S608 (table name is static)
        return cur.rowcount
