import uuid

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from kombu import Connection


def live(request):
    return JsonResponse({"status": "ok"})


def _check_db():
    with connection.cursor() as cur:
        cur.execute("SELECT 1")
    return True


def _check_cache():
    key = f"health:{uuid.uuid4().hex}"
    cache.set(key, "1", 5)
    ok = cache.get(key) == "1"
    cache.delete(key)
    return ok


def _check_broker():
    with Connection(settings.CELERY_BROKER_URL, connect_timeout=3) as conn:
        conn.ensure_connection(max_retries=1)
    return True


def ready(request):
    results = {}
    for name, fn in (("database", _check_db), ("cache", _check_cache), ("broker", _check_broker)):
        try:
            results[name] = "ok" if fn() else "fail"
        except Exception:  # noqa: BLE001
            results[name] = "fail"
    # Only the database removes a node from the load balancer; cache and broker degrade gracefully.
    return JsonResponse(results, status=200 if results["database"] == "ok" else 503)
