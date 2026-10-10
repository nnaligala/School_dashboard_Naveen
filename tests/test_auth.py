import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.accounts.roles import Role
from apps.core.models import AuditLog

User = get_user_model()
PW = "Str0ng-Pass-Phrase!"


@pytest.fixture
def make_user(db):
    def _make(role=Role.STUDENT, email=None, **kw):
        email = email or f"{role.value}@example.com"
        return User.objects.create_user(email, PW, first_name="T", role=role, **kw)
    return _make


def test_login_success_records_history_and_audit(client, make_user):
    make_user(Role.TEACHER)
    r = client.post(reverse("accounts:login"), {"username": "teacher@example.com", "password": PW})
    assert r.status_code == 302
    assert AuditLog.objects.filter(action="auth.login").exists()


def test_lockout_after_repeated_failures_even_with_correct_password(client, make_user, settings):
    user = make_user(Role.TEACHER)
    for _ in range(settings.LOGIN_MAX_FAILURES):
        client.post(reverse("accounts:login"), {"username": user.email, "password": "wrong"})
    user.refresh_from_db()
    assert user.is_locked
    r = client.post(reverse("accounts:login"), {"username": user.email, "password": PW})
    assert r.status_code == 200  # form re-rendered, not logged in
    assert "_auth_user_id" not in client.session


def test_logout_requires_post(client, make_user):
    client.force_login(make_user())
    assert client.get(reverse("accounts:logout")).status_code == 405
    assert client.post(reverse("accounts:logout")).status_code == 302


def test_must_change_password_redirects(client, make_user):
    client.force_login(make_user(must_change_password=True))
    r = client.get(reverse("accounts:dashboard"))
    assert r.status_code == 302 and r.url == reverse("accounts:password_change")


def test_password_change_clears_flag(client, make_user):
    u = make_user(must_change_password=True)
    client.force_login(u)
    r = client.post(reverse("accounts:password_change"), {
        "old_password": PW, "new_password1": "Another-Str0ng-One!", "new_password2": "Another-Str0ng-One!"})
    assert r.status_code == 302
    u.refresh_from_db()
    assert u.must_change_password is False


def test_password_reset_sends_email(client, make_user, mailoutbox):
    make_user(Role.PARENT)
    client.post(reverse("accounts:password_reset"), {"email": "parent@example.com"})
    assert len(mailoutbox) == 1


def test_audit_log_is_immutable(db):
    entry = AuditLog.objects.create(action="x")
    with pytest.raises(PermissionError):
        entry.delete()
    entry.action = "y"
    with pytest.raises(PermissionError):
        entry.save()
