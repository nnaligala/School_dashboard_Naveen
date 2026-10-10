import secrets

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.accounts.roles import Role

DEMO = [
    (Role.SCHOOL_ADMIN, "Anita", "Rao"),
    (Role.PRINCIPAL, "Rajesh", "Verma"),
    (Role.TEACHER, "Meera", "Iyer"),
    (Role.ACCOUNTANT, "Suresh", "Kumar"),
    (Role.LIBRARIAN, "Lakshmi", "Nair"),
    (Role.TRANSPORT_MANAGER, "Imran", "Khan"),
    (Role.RECEPTIONIST, "Divya", "Reddy"),
    (Role.STUDENT, "Arjun", "Sharma"),
    (Role.PARENT, "Kavita", "Sharma"),
]


class Command(BaseCommand):
    help = "Create one demo user per role (example.com addresses, fictional names)."

    def add_arguments(self, parser):
        parser.add_argument("--password", default=None, help="Shared demo password (random if omitted)")

    def handle(self, *args, **opts):
        User = get_user_model()
        password = opts["password"] or secrets.token_urlsafe(12)
        created = 0
        for role, first, last in DEMO:
            email = f"{role.value}@example.com"
            if User.objects.filter(email=email).exists():
                continue
            User.objects.create_user(email, password, first_name=first, last_name=last, role=role)
            created += 1
        self.stdout.write(self.style.SUCCESS(f"Created {created} demo users."))
        if created:
            self.stdout.write(f"Emails: <role>@example.com  (e.g. teacher@example.com)\nPassword: {password}")
