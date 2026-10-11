from datetime import timedelta

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone

from apps.attendance.models import AttendanceRecord
from apps.attendance.services import mark_attendance

pytestmark = pytest.mark.django_db


def today():
    return timezone.localdate()


class TestService:
    def test_marks_and_updates_without_duplicates(self, world):
        w = world
        mark_attendance(user=w["t1"], section=w["sec_a"], day=today(), entries={w["s_a"].pk: ("present", "")})
        mark_attendance(user=w["t1"], section=w["sec_a"], day=today(), entries={w["s_a"].pk: ("late", "bus")})
        recs = AttendanceRecord.objects.filter(student=w["s_a"])
        assert recs.count() == 1 and recs.get().status == "late"

    def test_teacher_cannot_mark_foreign_section(self, world):
        w = world
        with pytest.raises(PermissionDenied):
            mark_attendance(user=w["t1"], section=w["sec_b"], day=today(), entries={w["s_b"].pk: ("present", "")})

    def test_cross_section_student_rejected(self, world):
        w = world
        with pytest.raises(ValidationError):
            mark_attendance(user=w["t1"], section=w["sec_a"], day=today(), entries={w["s_b"].pk: ("present", "")})
        assert AttendanceRecord.objects.count() == 0

    def test_future_date_rejected(self, world):
        w = world
        with pytest.raises(ValidationError):
            mark_attendance(user=w["t1"], section=w["sec_a"], day=today() + timedelta(days=1), entries={w["s_a"].pk: ("present", "")})

    def test_invalid_status_rejected_atomically(self, world):
        w = world
        with pytest.raises(ValidationError):
            mark_attendance(user=w["t1"], section=w["sec_a"], day=today(),
                            entries={w["s_a"].pk: ("present", ""), w["s_a2"].pk: ("bogus", "")})
        assert AttendanceRecord.objects.count() == 0

    def test_parent_cannot_mark(self, world):
        w = world
        with pytest.raises(PermissionDenied):
            mark_attendance(user=w["p1"], section=w["sec_a"], day=today(), entries={})

    def test_absence_emails_guardian_once(self, world, django_capture_on_commit_callbacks, mailoutbox):
        w = world
        with django_capture_on_commit_callbacks(execute=True):
            mark_attendance(user=w["t1"], section=w["sec_a"], day=today(), entries={w["s_a"].pk: ("absent", "fever")})
        assert len(mailoutbox) == 1 and mailoutbox[0].to == ["p1@example.com"]
        with django_capture_on_commit_callbacks(execute=True):  # re-saving the same status must not re-notify
            mark_attendance(user=w["t1"], section=w["sec_a"], day=today(), entries={w["s_a"].pk: ("absent", "fever")})
        assert len(mailoutbox) == 1

    def test_db_unique_constraint(self, world):
        w = world
        AttendanceRecord.objects.create(student=w["s_a"], section=w["sec_a"], date=today(), status="present")
        with pytest.raises(IntegrityError), transaction.atomic():
            AttendanceRecord.objects.create(student=w["s_a"], section=w["sec_a"], date=today(), status="absent")

    def test_period_wise_records_coexist(self, world):
        w = world
        for p in (1, 2):
            mark_attendance(user=w["admin"], section=w["sec_a"], day=today(), period=p, entries={w["s_a"].pk: ("present", "")})
        assert AttendanceRecord.objects.filter(student=w["s_a"]).count() == 2


class TestViews:
    def url(self, name, sec):
        return reverse(f"attendance:{name}", args=[sec.public_id])

    def test_teacher_marks_via_form(self, client, world):
        w = world
        client.force_login(w["t1"])
        r = client.post(self.url("mark", w["sec_a"]), {
            "date": today().isoformat(), f"status_{w['s_a'].public_id}": "absent",
            f"status_{w['s_a2'].public_id}": "present"})
        assert r.status_code == 302
        assert AttendanceRecord.objects.get(student=w["s_a"]).status == "absent"

    def test_foreign_section_is_404(self, client, world):
        client.force_login(world["t1"])
        assert client.get(self.url("mark", world["sec_b"])).status_code == 404
        assert client.get(self.url("report", world["sec_b"])).status_code == 404

    def test_posting_other_sections_student_ignored(self, client, world):
        w = world
        client.force_login(w["t1"])
        client.post(self.url("mark", w["sec_a"]), {"date": today().isoformat(), f"status_{w['s_b'].public_id}": "absent"})
        assert AttendanceRecord.objects.count() == 0

    @pytest.mark.parametrize("who", ["p1", "stu", "accountant"])
    def test_non_staff_forbidden(self, client, world, who):
        client.force_login(world[who])
        assert client.get(reverse("attendance:sections")).status_code == 403
        assert client.get(self.url("mark", world["sec_a"])).status_code == 403

    def test_principal_can_view_report_not_mark(self, client, world):
        client.force_login(world["principal"])
        assert client.get(self.url("report", world["sec_a"])).status_code == 200
        assert client.get(self.url("mark", world["sec_a"])).status_code == 403

    def test_monthly_report_counts(self, client, world):
        w = world
        mark_attendance(user=w["t1"], section=w["sec_a"], day=today(), entries={w["s_a"].pk: ("absent", ""), w["s_a2"].pk: ("present", "")})
        client.force_login(w["t1"])
        r = client.get(self.url("report", w["sec_a"]))
        assert r.status_code == 200
        rows = {s.first_name: s for s in r.context["rows"]}
        assert rows["Asha"].absent == 1 and rows["Ravi"].present == 1

    def test_bad_date_falls_back(self, client, world):
        client.force_login(world["t1"])
        assert client.get(self.url("mark", world["sec_a"]) + "?date=garbage").status_code == 200

    def test_student_detail_shows_attendance(self, client, world):
        w = world
        mark_attendance(user=w["t1"], section=w["sec_a"], day=today(), entries={w["s_a"].pk: ("late", "bus")})
        client.force_login(w["p1"])
        assert b"bus" in client.get(reverse("students:detail", args=[w["s_a"].public_id])).content
