from datetime import date

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from apps.academics.selectors import sections_for
from apps.accounts.permissions import CapabilityRequiredMixin
from apps.students.models import Student

from .models import AttendanceRecord
from .services import mark_attendance


def _parse_date(value):
    try:
        return date.fromisoformat(value) if value else timezone.localdate()
    except ValueError:
        return timezone.localdate()


class SectionListView(CapabilityRequiredMixin, View):
    capability = "attendance.view"

    def get(self, request):
        return render(request, "attendance/sections.html", {"sections": sections_for(request.user)})


class MarkAttendanceView(CapabilityRequiredMixin, View):
    capability = "attendance.mark"

    def _section(self, request, public_id):
        return get_object_or_404(sections_for(request.user), public_id=public_id)

    def get(self, request, public_id):
        section = self._section(request, public_id)
        day = _parse_date(request.GET.get("date"))
        students = Student.objects.filter(section=section, status="active").order_by("first_name", "last_name")
        records = {r.student_id: r for r in AttendanceRecord.objects.filter(section=section, date=day, period=0)}
        rows = [(s, records.get(s.pk)) for s in students]
        return render(request, "attendance/mark.html", {
            "section": section, "day": day, "rows": rows, "statuses": AttendanceRecord.Status.choices})

    def post(self, request, public_id):
        section = self._section(request, public_id)
        day = _parse_date(request.POST.get("date"))
        entries = {}
        for s in Student.objects.filter(section=section, status="active"):
            status = request.POST.get(f"status_{s.public_id}")
            if status:
                entries[s.pk] = (status, request.POST.get(f"reason_{s.public_id}", ""))
        try:
            saved = mark_attendance(user=request.user, section=section, day=day, entries=entries)
            messages.success(request, f"Saved attendance for {saved} students.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect(f"{request.path}?date={day.isoformat()}")


class MonthlyReportView(CapabilityRequiredMixin, View):
    capability = "attendance.view"

    def get(self, request, public_id):
        section = get_object_or_404(sections_for(request.user), public_id=public_id)
        today = timezone.localdate()
        try:
            year, month = (int(x) for x in request.GET.get("month", f"{today:%Y-%m}").split("-"))
            date(year, month, 1)
        except (ValueError, TypeError):
            year, month = today.year, today.month
        in_month = Q(attendance__date__year=year, attendance__date__month=month, attendance__period=0)
        rows = Student.objects.filter(section=section, status="active").annotate(
            present=Count("attendance", filter=in_month & Q(attendance__status="present")),
            absent=Count("attendance", filter=in_month & Q(attendance__status="absent")),
            late=Count("attendance", filter=in_month & Q(attendance__status="late")),
            excused=Count("attendance", filter=in_month & Q(attendance__status="excused")),
        ).order_by("first_name")
        return render(request, "attendance/report.html", {"section": section, "rows": rows, "year": year, "month": month})
