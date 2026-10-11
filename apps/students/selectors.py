from apps.accounts.roles import Role
from apps.academics.selectors import sections_for

from .models import Student

SEES_ALL = {Role.SUPER_ADMIN, Role.SCHOOL_ADMIN, Role.PRINCIPAL, Role.RECEPTIONIST}


def students_for(user):
    """Students this user may see. Every student view/export MUST start from this queryset."""
    if user is None or not user.is_authenticated or not user.is_active:
        return Student.objects.none()
    qs = Student.objects.select_related("section__school_class", "section__academic_year")
    if user.role in SEES_ALL:
        return qs
    if user.role == Role.TEACHER:
        return qs.filter(section__in=sections_for(user))
    if user.role == Role.STUDENT:
        return qs.filter(user=user)
    if user.role == Role.PARENT:
        return qs.filter(guardians__user=user).distinct()
    return qs.none()
