import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.accounts.roles import Role
from apps.communication.tasks import send_email
from apps.core.tasks import purge_old_audit_logs
from apps.students.models import Student

User = get_user_model()


@pytest.mark.django_db
def test_seed_creates_all_roles_and_data_idempotently():
    call_command("seed_demo", "--password", "Demo-Passw0rd-Long!")
    call_command("seed_demo", "--password", "Demo-Passw0rd-Long!")
    roles = set(User.objects.values_list("role", flat=True))
    assert roles == {r.value for r in Role} - {Role.SUPER_ADMIN.value}
    assert Student.objects.count() == 6


@pytest.mark.django_db
def test_superuser_gets_super_admin_role():
    u = User.objects.create_superuser("root@example.com", "Str0ng-Pass-Phrase!", first_name="Root")
    assert u.role == Role.SUPER_ADMIN and u.is_staff


def test_send_email_task(mailoutbox):
    send_email.delay("Hi", "Body", ["a@example.com"])
    assert mailoutbox[0].to == ["a@example.com"]


@pytest.mark.django_db
def test_purge_task_runs():
    assert purge_old_audit_logs() == 0
