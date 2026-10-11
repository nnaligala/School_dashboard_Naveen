from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("password-change/", views.PasswordChangeView.as_view(), name="password_change"),
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="accounts/simple_form.html",
            email_template_name="accounts/password_reset_email.txt",
            subject_template_name="accounts/password_reset_subject.txt",
            success_url=reverse_lazy("accounts:password_reset_done"),
            extra_context={"title": "Reset your password"},
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/message.html",
            extra_context={"title": "Check your email", "message": "If that address has an account, a reset link is on its way."},
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/simple_form.html",
            success_url=reverse_lazy("accounts:password_reset_complete"),
            extra_context={"title": "Choose a new password"},
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/message.html",
            extra_context={"title": "Password updated", "message": "You can now sign in with your new password."},
        ),
        name="password_reset_complete",
    ),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("users/", views.UserListView.as_view(), name="user_list"),
    path("users/<uuid:public_id>/", views.UserDetailView.as_view(), name="user_detail"),
    path("audit/", views.AuditLogView.as_view(), name="audit_log"),
]
