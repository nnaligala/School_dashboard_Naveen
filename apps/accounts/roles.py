from django.db import models


class Role(models.TextChoices):
    SUPER_ADMIN = "super_admin", "Super Administrator"
    SCHOOL_ADMIN = "school_admin", "School Administrator"
    PRINCIPAL = "principal", "Principal"
    TEACHER = "teacher", "Teacher"
    ACCOUNTANT = "accountant", "Accountant"
    LIBRARIAN = "librarian", "Librarian"
    TRANSPORT_MANAGER = "transport_manager", "Transport Manager"
    RECEPTIONIST = "receptionist", "Receptionist"
    STUDENT = "student", "Student"
    PARENT = "parent", "Parent or Guardian"
