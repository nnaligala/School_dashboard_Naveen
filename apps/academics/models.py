from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

from apps.core.models import PublicIdModel, TimeStampedModel


class AcademicYear(TimeStampedModel):
    name = models.CharField(max_length=20, unique=True)  # e.g. "2026-27"
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ["-start_date"]
        constraints = [
            models.CheckConstraint(condition=Q(end_date__gt=F("start_date")), name="acad_year_dates_valid"),
            models.UniqueConstraint(fields=["is_current"], condition=Q(is_current=True), name="one_current_year"),
        ]

    def __str__(self):
        return self.name


class SchoolClass(TimeStampedModel):
    name = models.CharField(max_length=50, unique=True)  # e.g. "Grade 5"
    order = models.PositiveSmallIntegerField(unique=True)

    class Meta:
        ordering = ["order"]
        verbose_name = "class"
        verbose_name_plural = "classes"

    def __str__(self):
        return self.name


class Section(PublicIdModel, TimeStampedModel):
    school_class = models.ForeignKey(SchoolClass, on_delete=models.PROTECT, related_name="sections")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.PROTECT, related_name="sections")
    name = models.CharField(max_length=10)  # "A"
    class_teacher = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="class_teacher_of", limit_choices_to={"role": "teacher"},
    )
    capacity = models.PositiveSmallIntegerField(default=40)

    class Meta:
        ordering = ["school_class__order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["school_class", "academic_year", "name"], name="unique_section_per_year"),
            models.CheckConstraint(condition=Q(capacity__gt=0), name="section_capacity_positive"),
        ]

    def __str__(self):
        return f"{self.school_class} {self.name} ({self.academic_year})"

    def clean(self):
        if self.class_teacher_id and self.class_teacher.role != "teacher":
            raise ValidationError({"class_teacher": "Class teacher must have the Teacher role."})


class Subject(TimeStampedModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class TeachingAssignment(TimeStampedModel):
    teacher = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="teaching_assignments",
        limit_choices_to={"role": "teacher"},
    )
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="assignments")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="assignments")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["teacher", "section", "subject"], name="unique_teaching_assignment")
        ]

    def __str__(self):
        return f"{self.teacher} - {self.subject} - {self.section}"
