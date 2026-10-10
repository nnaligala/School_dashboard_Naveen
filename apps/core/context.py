from django.conf import settings

from apps.accounts.permissions import nav_for


def school(request):
    user = getattr(request, "user", None)
    return {
        "SCHOOL_NAME": settings.SCHOOL_NAME,
        "role_nav": nav_for(user) if user is not None and user.is_authenticated else [],
    }
