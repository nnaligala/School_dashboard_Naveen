from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.core.models import PublicIdModel, TimeStampedModel

from .roles import Role


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create(self, email, password, **extra):
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.update(is_staff=True, is_superuser=True, role=Role.SUPER_ADMIN)
        return self._create(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin, PublicIdModel, TimeStampedModel):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.STUDENT, db_index=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # Django admin access only

    must_change_password = models.BooleanField(default=False)
    failed_login_count = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name"]

    class Meta:
        indexes = [models.Index(fields=["role", "is_active"])]
        constraints = [
            models.CheckConstraint(condition=models.Q(role__in=[r.value for r in Role]), name="user_role_valid")
        ]

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_locked(self):
        return bool(self.locked_until and self.locked_until > timezone.now())

    def has_role(self, *roles):
        return self.is_active and self.role in {str(r) for r in roles}


class LoginHistory(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name="logins")
    email_attempted = models.CharField(max_length=254)
    success = models.BooleanField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["email_attempted", "-created_at"])]
