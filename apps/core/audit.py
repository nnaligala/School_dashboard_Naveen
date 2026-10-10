import logging

from .models import AuditLog

logger = logging.getLogger("audit")


def client_ip(request):
    if request is None:
        return None
    # Nginx sets X-Real-IP from the verified peer address; never trust client-supplied XFF.
    return request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR")


def record(action, *, request=None, actor=None, obj=None, **metadata):
    """Write an audit entry. Never raises into the calling request."""
    try:
        if actor is None and request is not None and request.user.is_authenticated:
            actor = request.user
        entry = AuditLog.objects.create(
            actor=actor,
            actor_label=getattr(actor, "email", "") if actor else "",
            action=action,
            object_type=obj.__class__.__name__ if obj is not None else "",
            object_id=str(getattr(obj, "public_id", getattr(obj, "pk", ""))) if obj is not None else "",
            ip_address=client_ip(request),
            metadata=metadata,
        )
        logger.info("action=%s actor=%s object=%s:%s", action, entry.actor_label, entry.object_type, entry.object_id)
        return entry
    except Exception:  # noqa: BLE001
        logger.exception("audit write failed action=%s", action)
        return None
