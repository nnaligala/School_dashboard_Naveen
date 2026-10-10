import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.accounts.permissions import can
from apps.accounts.roles import Role
from apps.core.models import AuditLog

User = get_user_model()
PW = "Str0ng-Pass-Phrase!"


def mk(role):
    return User.objects.create_user(f"{role.value}@example.com", PW, first_name="T", role=role)


@pytest.mark.django_db
class TestAccess:
    def test_anonymous_redirected_to_login(self, client):
        r = client.get(reverse("accounts:dashboard"))
        assert r.status_code == 302 and "/accounts/login/" in r.url

    @pytest.mark.parametrize("role", list(Role))
    def test_every_role_has_dashboard(self, client, role):
        client.force_login(mk(role))
        assert client.get(reverse("accounts:dashboard")).status_code == 200

    @pytest.mark.parametrize("role", [r for r in Role if r not in (Role.SUPER_ADMIN, Role.SCHOOL_ADMIN)])
    def test_non_admins_cannot_list_users(self, client, role):
        client.force_login(mk(role))
        assert client.get(reverse("accounts:user_list")).status_code == 403

    def test_admin_can_list_users(self, client):
        client.force_login(mk(Role.SCHOOL_ADMIN))
        assert client.get(reverse("accounts:user_list")).status_code == 200

    def test_denied_access_is_audited(self, client):
        client.force_login(mk(Role.STUDENT))
        client.get(reverse("accounts:user_list"))
        assert AuditLog.objects.filter(action="access.denied").exists()

    def test_idor_user_cannot_view_another_users_profile(self, client):
        student, parent = mk(Role.STUDENT), mk(Role.PARENT)
        client.force_login(student)
        assert client.get(reverse("accounts:user_detail", args=[parent.public_id])).status_code == 404
        assert client.get(reverse("accounts:user_detail", args=[student.public_id])).status_code == 200

    def test_admin_can_view_any_profile(self, client):
        admin, student = mk(Role.SCHOOL_ADMIN), mk(Role.STUDENT)
        client.force_login(admin)
        assert client.get(reverse("accounts:user_detail", args=[student.public_id])).status_code == 200

    def test_audit_log_restricted(self, client):
        client.force_login(mk(Role.TEACHER))
        assert client.get(reverse("accounts:audit_log")).status_code == 403
        client.force_login(mk(Role.PRINCIPAL))
        assert client.get(reverse("accounts:audit_log")).status_code == 200


@pytest.mark.django_db
def test_capability_matrix():
    assert can(mk(Role.ACCOUNTANT), "fees.manage")
    assert not can(mk(Role.TEACHER), "fees.manage")
    assert not can(mk(Role.STUDENT), "students.view")
    assert not can(None, "fees.manage")


@pytest.mark.django_db
def test_inactive_user_has_no_capabilities():
    u = mk(Role.SCHOOL_ADMIN)
    u.is_active = False
    assert not can(u, "users.manage")
