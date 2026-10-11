import csv
import io
from datetime import date

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.academics.models import AcademicYear, Section
from apps.core import audit

from .models import AdmissionSequence, Student

MAX_IMPORT_ROWS = 500
REQUIRED_COLUMNS = {"first_name", "last_name", "date_of_birth", "gender", "class", "section"}


@transaction.atomic
def next_admission_number(year=None):
    year = year or timezone.localdate().year
    seq, _ = AdmissionSequence.objects.select_for_update().get_or_create(year=year)
    seq.last_number += 1
    seq.save(update_fields=["last_number"])
    return f"NS{year}{seq.last_number:04d}"


@transaction.atomic
def create_student(*, actor=None, request=None, **fields):
    student = Student.objects.create(admission_number=next_admission_number(), **fields)
    audit.record("student.created", request=request, actor=actor, obj=student)
    return student


@transaction.atomic
def promote_section(*, from_section, to_section, actor):
    """Move every active student of one section to another in a single transaction."""
    if from_section.pk == to_section.pk:
        raise ValidationError("Source and target sections must differ.")
    if to_section.academic_year_id == from_section.academic_year_id:
        raise ValidationError("Target section must belong to a different academic year.")
    ids = list(Student.objects.select_for_update().filter(section=from_section, status="active").values_list("pk", flat=True))
    Student.objects.filter(pk__in=ids).update(section=to_section)
    audit.record("student.promoted", actor=actor, count=len(ids), source=str(from_section), target=str(to_section))
    return len(ids)


def safe_cell(value):
    """Neutralise spreadsheet formula injection in exported CSV cells."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def export_students_csv(students, stream):
    writer = csv.writer(stream)
    writer.writerow(["admission_number", "first_name", "last_name", "class", "section", "status"])
    for s in students:
        writer.writerow([
            safe_cell(s.admission_number), safe_cell(s.first_name), safe_cell(s.last_name),
            safe_cell(s.section.school_class.name if s.section else ""),
            safe_cell(s.section.name if s.section else ""), s.status,
        ])


def import_students_csv(text, *, actor):
    """All-or-nothing import. Returns (created_count, errors). Nothing is saved if any row is invalid."""
    if actor is None or actor.role not in ("super_admin", "school_admin"):
        raise PermissionDenied
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(set(reader.fieldnames)):
        return 0, [f"Header must contain: {', '.join(sorted(REQUIRED_COLUMNS))}"]
    year = AcademicYear.objects.filter(is_current=True).first()
    if year is None:
        return 0, ["No current academic year is configured."]
    sections = {(s.school_class.name, s.name): s for s in Section.objects.filter(academic_year=year).select_related("school_class")}
    parsed, errors = [], []
    for line, row in enumerate(reader, start=2):
        if line - 1 > MAX_IMPORT_ROWS:
            errors.append(f"Too many rows (max {MAX_IMPORT_ROWS}).")
            break
        first = (row.get("first_name") or "").strip()
        gender = (row.get("gender") or "").strip().upper()[:1]
        section = sections.get(((row.get("class") or "").strip(), (row.get("section") or "").strip()))
        try:
            dob = date.fromisoformat((row.get("date_of_birth") or "").strip())
        except ValueError:
            dob = None
        problems = []
        if not first:
            problems.append("first_name missing")
        if dob is None or dob >= timezone.localdate():
            problems.append("date_of_birth must be a past date (YYYY-MM-DD)")
        if gender not in ("M", "F", "O"):
            problems.append("gender must be M, F or O")
        if section is None:
            problems.append("unknown class/section for the current year")
        if problems:
            errors.append(f"Line {line}: " + "; ".join(problems))
        else:
            parsed.append(dict(first_name=first, last_name=(row.get("last_name") or "").strip(),
                               date_of_birth=dob, gender=gender, section=section))
    if errors:
        return 0, errors
    with transaction.atomic():
        for fields in parsed:
            create_student(actor=actor, **fields)
        audit.record("student.bulk_import", actor=actor, count=len(parsed))
    return len(parsed), []
