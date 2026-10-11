from django.urls import path

from . import views

app_name = "students"

urlpatterns = [
    path("", views.StudentListView.as_view(), name="list"),
    path("export.csv", views.StudentExportView.as_view(), name="export"),
    path("import/", views.StudentImportView.as_view(), name="import"),
    path("<uuid:public_id>/", views.StudentDetailView.as_view(), name="detail"),
]
