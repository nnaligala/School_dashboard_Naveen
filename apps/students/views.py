from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import DetailView, ListView

from apps.accounts.permissions import CapabilityRequiredMixin, can
from apps.attendance.models import AttendanceRecord
from apps.core import audit

from .forms import CSVImportForm
from .selectors import students_for
from .services import export_students_csv, import_students_csv


class StudentListView(LoginRequiredMixin, ListView):
    template_name = "students/list.html"
    context_object_name = "students"
    paginate_by = 25

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["perms_students_view"] = can(self.request.user, "students.view")
        ctx["perms_students_manage"] = can(self.request.user, "students.manage")
        return ctx

    def get_queryset(self):
        qs = students_for(self.request.user)
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(admission_number__icontains=q))
        return qs.order_by("first_name", "last_name")


class StudentDetailView(LoginRequiredMixin, DetailView):
    """Looked up inside the user's scoped queryset, so out-of-scope IDs return 404."""

    template_name = "students/detail.html"
    context_object_name = "student"
    slug_field = "public_id"
    slug_url_kwarg = "public_id"

    def get_queryset(self):
        return students_for(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["can_view_medical"] = can(self.request.user, "students.medical")
        ctx["recent_attendance"] = AttendanceRecord.objects.filter(student=self.object, period=0).order_by("-date")[:30]
        ctx["guardians"] = self.object.guardians.select_related("user")
        return ctx


class StudentExportView(CapabilityRequiredMixin, View):
    capability = "students.view"

    def get(self, request):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="students.csv"'
        export_students_csv(students_for(request.user).order_by("admission_number"), response)
        audit.record("student.export", request=request)
        return response


class StudentImportView(CapabilityRequiredMixin, View):
    capability = "students.manage"
    template_name = "students/import.html"

    def get(self, request):
        return render(request, self.template_name, {"form": CSVImportForm()})

    def post(self, request):
        form = CSVImportForm(request.POST, request.FILES)
        errors = []
        if form.is_valid():
            created, errors = import_students_csv(form.cleaned_data["file"], actor=request.user)
            if not errors:
                messages.success(request, f"Imported {created} students.")
                return redirect("students:list")
        return render(request, self.template_name, {"form": form, "errors": errors})
