from django.db import models
from django.db.models import Q

from apps.core.models import TimeStampedModel


class AttendanceRecord(TimeStampedModel):
    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"
        LATE = "late", "Late"
        EXCUSED = "excused", "Excused"

    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="attendance")
    section = models.ForeignKey("academics.Section", on_delete=models.PROTECT, related_name="attendance")
    date = models.DateField(db_index=True)
    period = models.PositiveSmallIntegerField(default=0, help_text="0 = whole-day register")
    status = models.CharField(max_length=10, choices=Status.choices)
    reason = models.CharField(max_length=200, blank=True)
    marked_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["student", "date", "period"], name="unique_attendance_per_period"),
            models.CheckConstraint(condition=Q(status__in=["present", "absent", "late", "excused"]), name="attendance_status_valid"),
        ]
        indexes = [models.Index(fields=["section", "date"])]
