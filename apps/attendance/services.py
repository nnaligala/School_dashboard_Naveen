from datetime import date as date_cls

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.academics.selectors import sections_for
from apps.communication.tasks import send_email
from apps.core import audit
from apps.students.models import Guardian, Student

from .models import AttendanceRecord

VALID = {c for c, _ in AttendanceRecord.Status.choices}


def _notify_absence(student, day):
    emails = list(Guardian.objects.filter(student=student).values_list("user__email", flat=True))
    if emails:
        send_email.delay(
            f"Absence notice: {student.full_name}",
            f"Dear parent/guardian,\n\n{student.full_name} was marked absent on {day:%d %b %Y}.\n\nNaveen's School",
            emails,
        )


def mark_attendance(*, user, section, day, entries, period=0):
    """entries: {student_pk: (status, reason)}. Returns number of rows saved.

    Enforces: the user may work with this section; the date is not in the future; every
    student actually belongs to the section (prevents cross-section writes).
    """
    if not sections_for(user).filter(pk=section.pk).exists():
        raise PermissionDenied
    if not isinstance(day, date_cls) or day > timezone.localdate():
        raise ValidationError("Attendance cannot be marked for a future date.")
    allowed = set(Student.objects.filter(section=section, status="active").values_list("pk", flat=True))
    for sid, (status, _reason) in entries.items():
        if sid not in allowed:
            raise ValidationError("A student in the submission does not belong to this section.")
        if status not in VALID:
            raise ValidationError(f"Invalid status '{status}'.")
    with transaction.atomic():
        existing = {r.student_id: r.status for r in AttendanceRecord.objects.filter(
            student_id__in=entries, date=day, period=period)}
        newly_absent = []
        for sid, (status, reason) in entries.items():
            AttendanceRecord.objects.update_or_create(
                student_id=sid, date=day, period=period,
                defaults={"status": status, "reason": reason[:200], "section": section, "marked_by": user},
            )
            if status == "absent" and existing.get(sid) != "absent":
                newly_absent.append(sid)
        audit.record("attendance.marked", actor=user, section=str(section), date=day.isoformat(), count=len(entries))
        for student in Student.objects.filter(pk__in=newly_absent):
            transaction.on_commit(lambda s=student: _notify_absence(s, day), robust=True)
    return len(entries)
