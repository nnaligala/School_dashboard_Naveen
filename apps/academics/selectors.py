from django.db.models import Q

from apps.accounts.roles import Role

from .models import Section

FULL_ACCESS = {Role.SUPER_ADMIN, Role.SCHOOL_ADMIN, Role.PRINCIPAL}


def sections_for(user):
    """Sections this user may work with. Single source of truth for section-level scoping."""
    if user is None or not user.is_authenticated or not user.is_active:
        return Section.objects.none()
    qs = Section.objects.select_related("school_class", "academic_year")
    if user.role in FULL_ACCESS:
        return qs
    if user.role == Role.TEACHER:
        return qs.filter(Q(class_teacher=user) | Q(assignments__teacher=user)).distinct()
    return qs.none()
