import io
from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse

from apps.academics.models import AcademicYear, Section
from apps.students.models import Student
from apps.students.selectors import students_for
from apps.students.services import (export_students_csv, import_students_csv, next_admission_number,
                                    promote_section, safe_cell)

pytestmark = pytest.mark.django_db


def detail(s):
    return reverse("students:detail", args=[s.public_id])


class TestAdmissionNumbers:
    def test_sequential_and_unique(self, world):
        nums = [next_admission_number(2030) for _ in range(3)]
        assert nums == ["NS20300001", "NS20300002", "NS20300003"]
        assert len({s.admission_number for s in Student.objects.all()}) == Student.objects.count()


class TestVisibility:
    def test_teacher_sees_only_own_sections(self, world):
        assert set(students_for(world["t1"])) == {world["s_a"], world["s_a2"]}
        # t2 is class teacher of B and teaches A via assignment
        assert set(students_for(world["t2"])) == {world["s_a"], world["s_a2"], world["s_b"]}

    def test_parent_and_student_scope(self, world):
        assert list(students_for(world["p1"])) == [world["s_a"]]
        assert list(students_for(world["p2"])) == [world["s_b"]]
        assert list(students_for(world["stu"])) == [world["s_a"]]

    def test_accountant_sees_nothing(self, world):
        assert not students_for(world["accountant"]).exists()

    def test_soft_deleted_students_hidden(self, world):
        world["s_b"].delete()
        assert world["s_b"] not in students_for(world["admin"])
        assert Student.all_objects.filter(pk=world["s_b"].pk).exists()


class TestIDOR:
    def test_parent_cannot_open_other_childs_page(self, client, world):
        client.force_login(world["p1"])
        assert client.get(detail(world["s_a"])).status_code == 200
        assert client.get(detail(world["s_b"])).status_code == 404

    def test_teacher_cannot_open_other_section_student(self, client, world):
        client.force_login(world["t1"])
        assert client.get(detail(world["s_b"])).status_code == 404

    def test_student_cannot_open_classmate(self, client, world):
        client.force_login(world["stu"])
        assert client.get(detail(world["s_a2"])).status_code == 404

    def test_list_is_scoped(self, client, world):
        client.force_login(world["p1"])
        body = client.get(reverse("students:list")).content.decode()
        assert "Asha" in body and "Bina" not in body

    def test_anonymous_redirected(self, client, world):
        assert client.get(detail(world["s_a"])).status_code == 302


class TestMedicalNotes:
    def test_hidden_from_teacher_parent_visible_to_admin(self, client, world):
        for who, expect in (("t1", False), ("p1", False), ("admin", True), ("principal", True)):
            client.force_login(world[who])
            assert ("Peanut allergy" in client.get(detail(world["s_a"])).content.decode()) is expect, who


class TestCSV:
    def _setup(self, world):
        return world["admin"]

    def test_import_valid(self, world):
        text = "first_name,last_name,date_of_birth,gender,class,section\nNeel,Roy,2015-04-01,M,Grade 5,A\nMina,Sen,2015-05-02,F,Grade 5,B\n"
        before = Student.objects.count()
        created, errors = import_students_csv(text, actor=world["admin"])
        assert (created, errors) == (2, [])
        assert Student.objects.count() == before + 2

    def test_import_is_all_or_nothing(self, world):
        text = "first_name,last_name,date_of_birth,gender,class,section\nNeel,Roy,2015-04-01,M,Grade 5,A\nBad,Row,not-a-date,X,Grade 9,Z\n"
        before = Student.objects.count()
        created, errors = import_students_csv(text, actor=world["admin"])
        assert created == 0 and len(errors) == 1 and "Line 3" in errors[0]
        assert Student.objects.count() == before

    def test_import_requires_admin_role(self, world):
        from django.core.exceptions import PermissionDenied
        with pytest.raises(PermissionDenied):
            import_students_csv("a,b\n", actor=world["t1"])

    def test_import_view_forbidden_for_teacher(self, client, world):
        client.force_login(world["t1"])
        assert client.get(reverse("students:import")).status_code == 403

    def test_import_view_upload(self, client, world):
        client.force_login(world["admin"])
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile("s.csv", b"first_name,last_name,date_of_birth,gender,class,section\nNeel,Roy,2015-04-01,M,Grade 5,A\n")
        r = client.post(reverse("students:import"), {"file": f})
        assert r.status_code == 302
        bad = SimpleUploadedFile("s.exe", b"x")
        assert client.post(reverse("students:import"), {"file": bad}).status_code == 200

    def test_export_scoped_and_without_medical(self, client, world):
        client.force_login(world["t1"])
        r = client.get(reverse("students:export"))
        text = r.content.decode()
        assert "Asha" in text and "Bina" not in text and "Peanut" not in text

    def test_export_blocked_for_parent(self, client, world):
        client.force_login(world["p1"])
        assert client.get(reverse("students:export")).status_code == 403

    def test_formula_injection_neutralised(self):
        assert safe_cell("=cmd|' /C calc'!A0").startswith("'=")
        assert safe_cell("Normal") == "Normal"


class TestPromotion:
    def test_promote_moves_active_students(self, world):
        year2 = AcademicYear.objects.create(name="2027-28", start_date=date(2027, 6, 1), end_date=date(2028, 3, 31))
        target = Section.objects.create(school_class=world["klass"], academic_year=year2, name="A")
        n = promote_section(from_section=world["sec_a"], to_section=target, actor=world["admin"])
        assert n == 2
        assert Student.objects.filter(section=target).count() == 2

    def test_promote_same_year_rejected(self, world):
        with pytest.raises(ValidationError):
            promote_section(from_section=world["sec_a"], to_section=world["sec_b"], actor=world["admin"])


class TestConstraints:
    def test_single_current_year(self, world):
        with pytest.raises(IntegrityError), transaction.atomic():
            AcademicYear.objects.create(name="2028-29", start_date=date(2028, 6, 1), end_date=date(2029, 3, 1), is_current=True)

    def test_bad_year_dates(self, world):
        with pytest.raises(IntegrityError), transaction.atomic():
            AcademicYear.objects.create(name="bad", start_date=date(2030, 1, 1), end_date=date(2029, 1, 1))

    def test_duplicate_section_rejected(self, world):
        with pytest.raises(IntegrityError), transaction.atomic():
            Section.objects.create(school_class=world["klass"], academic_year=world["year"], name="A")

    def test_export_helper(self, world):
        buf = io.StringIO()
        export_students_csv(Student.objects.select_related("section__school_class"), buf)
        assert "admission_number" in buf.getvalue()
