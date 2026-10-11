from datetime import date

import pytest
from django.contrib.auth import get_user_model

from apps.academics.models import AcademicYear, SchoolClass, Section, Subject, TeachingAssignment
from apps.accounts.roles import Role
from apps.students.models import Guardian
from apps.students.services import create_student

User = get_user_model()
PW = "Str0ng-Pass-Phrase!"


@pytest.fixture
def world(db):
    """Two sections, two teachers, students, and two parents."""
    mk = lambda role, email, **kw: User.objects.create_user(email, PW, first_name=email.split("@")[0], role=role, **kw)  # noqa: E731
    year = AcademicYear.objects.create(name="2026-27", start_date=date(2026, 6, 1), end_date=date(2027, 3, 31), is_current=True)
    klass = SchoolClass.objects.create(name="Grade 5", order=5)
    t1, t2 = mk(Role.TEACHER, "t1@example.com"), mk(Role.TEACHER, "t2@example.com")
    sec_a = Section.objects.create(school_class=klass, academic_year=year, name="A", class_teacher=t1)
    sec_b = Section.objects.create(school_class=klass, academic_year=year, name="B", class_teacher=t2)
    s_a = create_student(first_name="Asha", last_name="One", date_of_birth=date(2015, 1, 1), gender="F", section=sec_a, medical_notes="Peanut allergy")
    s_a2 = create_student(first_name="Ravi", last_name="Two", date_of_birth=date(2015, 2, 1), gender="M", section=sec_a)
    s_b = create_student(first_name="Bina", last_name="Three", date_of_birth=date(2015, 3, 1), gender="F", section=sec_b)
    p1, p2 = mk(Role.PARENT, "p1@example.com"), mk(Role.PARENT, "p2@example.com")
    Guardian.objects.create(user=p1, student=s_a)
    Guardian.objects.create(user=p2, student=s_b)
    stu_user = mk(Role.STUDENT, "stu@example.com")
    s_a.user = stu_user
    s_a.save()
    subj = Subject.objects.create(name="Maths", code="MATH")
    TeachingAssignment.objects.create(teacher=t2, section=sec_a, subject=subj)  # t2 also teaches section A
    return dict(year=year, klass=klass, t1=t1, t2=t2, sec_a=sec_a, sec_b=sec_b, s_a=s_a, s_a2=s_a2, s_b=s_b,
                p1=p1, p2=p2, stu=stu_user, admin=mk(Role.SCHOOL_ADMIN, "adm@example.com"),
                principal=mk(Role.PRINCIPAL, "pri@example.com"), accountant=mk(Role.ACCOUNTANT, "acc@example.com"))
