from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import DetailView, ListView, TemplateView

from apps.core import audit
from apps.core.models import AuditLog

from .forms import EmailLoginForm
from .models import User
from .permissions import ROLE_SUMMARY, CapabilityRequiredMixin, can, capabilities_of
from .roles import Role


class LoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    authentication_form = EmailLoginForm
    redirect_authenticated_user = True


class LogoutView(auth_views.LogoutView):
    """POST only (Django 5)."""


class PasswordChangeView(auth_views.PasswordChangeView):
    template_name = "accounts/simple_form.html"
    success_url = reverse_lazy("accounts:dashboard")
    extra_context = {"title": "Change password"}

    def form_valid(self, form):
        response = super().form_valid(form)
        User.objects.filter(pk=self.request.user.pk).update(
            must_change_password=False, password_changed_at=timezone.now()
        )
        audit.record("auth.password_changed", request=self.request)
        return response


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx["role_label"] = Role(user.role).label
        ctx["role_summary"] = ROLE_SUMMARY[Role(user.role)]
        ctx["capabilities"] = capabilities_of(user)
        return ctx


class ProfileView(LoginRequiredMixin, DetailView):
    template_name = "accounts/user_detail.html"
    context_object_name = "subject"

    def get_object(self, queryset=None):
        return self.request.user


class UserListView(CapabilityRequiredMixin, ListView):
    capability = "users.manage"
    template_name = "accounts/user_list.html"
    queryset = User.objects.order_by("email")
    paginate_by = 25
    context_object_name = "users"


class UserDetailView(LoginRequiredMixin, DetailView):
    """Object-level rule: a user may view only themselves; user managers may view anyone.
    Everyone else gets 404 (not 403) so valid IDs cannot be probed."""

    template_name = "accounts/user_detail.html"
    context_object_name = "subject"
    slug_field = "public_id"
    slug_url_kwarg = "public_id"
    queryset = User.objects.all()

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.pk != self.request.user.pk and not can(self.request.user, "users.manage"):
            audit.record("access.denied", request=self.request, path=self.request.path)
            raise Http404
        return obj


class AuditLogView(CapabilityRequiredMixin, ListView):
    capability = "audit.view"
    template_name = "accounts/audit_log.html"
    queryset = AuditLog.objects.all()[:200]
    context_object_name = "entries"
