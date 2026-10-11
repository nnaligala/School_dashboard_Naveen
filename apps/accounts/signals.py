from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models import F
from django.dispatch import receiver
from django.utils import timezone

from apps.core import audit

from .models import LoginHistory


def _meta(request):
    if request is None:
        return None, ""
    return audit.client_ip(request), request.META.get("HTTP_USER_AGENT", "")[:300]


@receiver(user_logged_in)
def on_login(sender, request, user, **kwargs):
    ip, ua = _meta(request)
    type(user).objects.filter(pk=user.pk).update(failed_login_count=0, locked_until=None)
    LoginHistory.objects.create(user=user, email_attempted=user.email, success=True, ip_address=ip, user_agent=ua)
    audit.record("auth.login", request=request, actor=user)


@receiver(user_logged_out)
def on_logout(sender, request, user, **kwargs):
    if user:
        audit.record("auth.logout", request=request, actor=user)


@receiver(user_login_failed)
def on_failed(sender, credentials, request=None, **kwargs):
    email = (credentials.get("username") or credentials.get("email") or "").lower()[:254]
    ip, ua = _meta(request)
    User = get_user_model()
    user = User.objects.filter(email=email).first()
    LoginHistory.objects.create(user=user, email_attempted=email, success=False, ip_address=ip, user_agent=ua)
    if user:
        User.objects.filter(pk=user.pk).update(failed_login_count=F("failed_login_count") + 1)
        user.refresh_from_db(fields=["failed_login_count"])
        if user.failed_login_count >= settings.LOGIN_MAX_FAILURES and not user.is_locked:
            until = timezone.now() + timedelta(minutes=settings.LOGIN_LOCK_MINUTES)
            User.objects.filter(pk=user.pk).update(locked_until=until)
            audit.record("auth.locked", request=request, actor=user, until=until.isoformat())
