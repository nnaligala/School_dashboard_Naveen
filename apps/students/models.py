from django.db import models
from django.db.models import Q

from apps.core.models import PublicIdModel, SoftDeleteModel, TimeStampedModel


class AdmissionSequence(models.Model):
    """One row per calendar year; locked with SELECT ... FOR UPDATE to issue unique numbers."""

    year = models.PositiveSmallIntegerField(unique=True)
    last_number = models.PositiveIntegerField(default=0)


class Student(PublicIdModel, TimeStampedModel, SoftDeleteModel):
    class Gender(models.TextChoices):
        MALE = "M", "Male"
        FEMALE = "F", "Female"
        OTHER = "O", "Other"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        TRANSFERRED = "transferred", "Transferred out"
        ALUMNI = "alumni", "Alumni"

    admission_number = models.CharField(max_length=20, unique=True, editable=False)
    user = models.OneToOneField(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="student_profile"
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=Gender.choices)
    section = models.ForeignKey(
        "academics.Section", null=True, blank=True, on_delete=models.PROTECT, related_name="students"
    )
    admission_date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    medical_notes = models.TextField(blank=True)  # restricted: see "students.medical" capability

    class Meta:
        ordering = ["first_name", "last_name"]
        indexes = [models.Index(fields=["section", "status"])]
        constraints = [models.CheckConstraint(condition=Q(gender__in=["M", "F", "O"]), name="student_gender_valid")]

    def __str__(self):
        return f"{self.full_name} ({self.admission_number})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class Guardian(TimeStampedModel):
    class Relationship(models.TextChoices):
        FATHER = "father", "Father"
        MOTHER = "mother", "Mother"
        GUARDIAN = "guardian", "Guardian"

    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="wards", limit_choices_to={"role": "parent"}
    )
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="guardians")
    relationship = models.CharField(max_length=12, choices=Relationship.choices, default=Relationship.GUARDIAN)
    is_primary = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "student"], name="unique_guardian_link")]

    def __str__(self):
        return f"{self.user} -> {self.student}"
