import secrets
from datetime import date

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.academics.models import AcademicYear, SchoolClass, Section, Subject, TeachingAssignment
from apps.accounts.roles import Role
from apps.students.models import Guardian, Student
from apps.students.services import create_student

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
STUDENTS = [  # fictional names; (first, last, gender, class, section)
    ("Arjun", "Sharma", "M", "Grade 5", "A"), ("Diya", "Menon", "F", "Grade 5", "A"),
    ("Rohan", "Das", "M", "Grade 5", "A"), ("Sana", "Ali", "F", "Grade 5", "B"),
    ("Karthik", "Pillai", "M", "Grade 5", "B"), ("Ishita", "Joshi", "F", "Grade 6", "A"),
]


class Command(BaseCommand):
    help = "Create demo users (one per role), a current academic year, classes, sections, and students."

    def add_arguments(self, parser):
        parser.add_argument("--password", default=None, help="Shared demo password (random if omitted)")

    @transaction.atomic
    def handle(self, *args, **opts):
        User = get_user_model()
        password = opts["password"] or secrets.token_urlsafe(12)
        created = 0
        for role, first, last in DEMO:
            email = f"{role.value}@example.com"
            if not User.objects.filter(email=email).exists():
                User.objects.create_user(email, password, first_name=first, last_name=last, role=role)
                created += 1

        year, _ = AcademicYear.objects.get_or_create(
            name="2026-27", defaults=dict(start_date=date(2026, 6, 1), end_date=date(2027, 3, 31), is_current=True))
        teacher = User.objects.get(email="teacher@example.com")
        sections = {}
        for order, cname in enumerate(["Grade 5", "Grade 6"], start=5):
            klass, _ = SchoolClass.objects.get_or_create(name=cname, defaults={"order": order})
            for sname in ("A", "B"):
                sec, _ = Section.objects.get_or_create(school_class=klass, academic_year=year, name=sname)
                sections[(cname, sname)] = sec
        sections[("Grade 5", "A")].class_teacher = teacher
        sections[("Grade 5", "A")].save()
        for code, name in (("MATH", "Mathematics"), ("ENG", "English"), ("SCI", "Science")):
            subj, _ = Subject.objects.get_or_create(code=code, defaults={"name": name})
            TeachingAssignment.objects.get_or_create(teacher=teacher, section=sections[("Grade 5", "A")], subject=subj)

        if not Student.all_objects.exists():
            for first, last, gender, cname, sname in STUDENTS:
                student = create_student(first_name=first, last_name=last, date_of_birth=date(2015, 5, 12),
                                         gender=gender, section=sections[(cname, sname)])
                if first == "Arjun":
                    student.user = User.objects.get(email="student@example.com")
                    student.save(update_fields=["user"])
                    Guardian.objects.create(user=User.objects.get(email="parent@example.com"), student=student,
                                            relationship="mother", is_primary=True)
        self.stdout.write(self.style.SUCCESS(f"Created {created} demo users; academic data ready."))
        if created:
            self.stdout.write(f"Emails: <role>@example.com  (e.g. teacher@example.com)\nPassword: {password}")
