from django.contrib.auth.backends import ModelBackend


class LockoutAwareBackend(ModelBackend):
    """Rejects locked accounts even when the password is correct."""

    def user_can_authenticate(self, user):
        return super().user_can_authenticate(user) and not user.is_locked
