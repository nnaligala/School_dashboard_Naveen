from django.urls import path

from . import views

app_name = "attendance"

urlpatterns = [
    path("", views.SectionListView.as_view(), name="sections"),
    path("<uuid:public_id>/mark/", views.MarkAttendanceView.as_view(), name="mark"),
    path("<uuid:public_id>/report/", views.MonthlyReportView.as_view(), name="report"),
]
