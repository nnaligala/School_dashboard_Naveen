"""Role -> capability matrix. Every view checks a capability on the server side."""
from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from apps.core import audit

from .roles import Role

R = Role
ADMINS = {R.SUPER_ADMIN, R.SCHOOL_ADMIN}
LEADERSHIP = ADMINS | {R.PRINCIPAL}

CAPABILITIES = {
    "users.manage": ADMINS,
    "audit.view": LEADERSHIP,
    "students.view": LEADERSHIP | {R.TEACHER, R.RECEPTIONIST},
    "students.manage": ADMINS,
    "attendance.view": LEADERSHIP | {R.TEACHER},
    "students.medical": {R.SUPER_ADMIN, R.SCHOOL_ADMIN, R.PRINCIPAL},
    "attendance.mark": ADMINS | {R.TEACHER},
    "exams.enter_marks": ADMINS | {R.TEACHER},
    "exams.approve": LEADERSHIP,
    "fees.manage": ADMINS | {R.ACCOUNTANT},
    "library.manage": ADMINS | {R.LIBRARIAN},
    "transport.manage": ADMINS | {R.TRANSPORT_MANAGER},
    "admissions.review": LEADERSHIP | {R.RECEPTIONIST},
    "notices.publish": LEADERSHIP | {R.TEACHER},
}

ROLE_SUMMARY = {
    R.SUPER_ADMIN: "Full control of the system, users, and audit trail.",
    R.SCHOOL_ADMIN: "Run daily operations: users, admissions, academics, fees.",
    R.PRINCIPAL: "Oversight of academics, approvals, results, and audit logs.",
    R.TEACHER: "Mark attendance, enter marks, and publish class notices.",
    R.ACCOUNTANT: "Fee structures, invoices, payments, and financial reports.",
    R.LIBRARIAN: "Catalogue, issue and return books, and library reports.",
    R.TRANSPORT_MANAGER: "Vehicles, routes, drivers, and student transport.",
    R.RECEPTIONIST: "Enquiries, admissions desk, and visitor handling.",
    R.STUDENT: "Your own timetable, homework, results, and notices.",
    R.PARENT: "Your child's attendance, fees, results, and notices.",
}


def can(user, capability):
    if user is None or not user.is_authenticated or not user.is_active:
        return False
    return user.role in CAPABILITIES.get(capability, set())


def capabilities_of(user):
    return sorted(c for c in CAPABILITIES if can(user, c))


def nav_for(user):
    items = [("Dashboard", "accounts:dashboard"), ("My profile", "accounts:profile")]
    if can(user, "users.manage"):
        items.append(("Users", "accounts:user_list"))
    if can(user, "students.view"):
        items.append(("Students", "students:list"))
    elif user.role == Role.PARENT:
        items.append(("My children", "students:list"))
    elif user.role == Role.STUDENT:
        items.append(("My record", "students:list"))
    if can(user, "attendance.view"):
        items.append(("Attendance", "attendance:sections"))
    if can(user, "audit.view"):
        items.append(("Audit log", "accounts:audit_log"))
    return items


class CapabilityRequiredMixin(AccessMixin):
    capability = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not can(request.user, self.capability):
            audit.record("access.denied", request=request, path=request.path, capability=self.capability)
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class HasCapability(BasePermission):
    """DRF permission: set `required_capability` on the view."""

    def has_permission(self, request, view):
        return can(request.user, getattr(view, "required_capability", None))
