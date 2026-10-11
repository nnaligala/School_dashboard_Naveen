from django.contrib import admin

from .models import Guardian, Student


class GuardianInline(admin.TabularInline):
    model = Guardian
    extra = 0


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("admission_number", "full_name", "section", "status")
    list_filter = ("status", "section__school_class")
    search_fields = ("admission_number", "first_name", "last_name")
    readonly_fields = ("admission_number",)
    inlines = [GuardianInline]

    def get_queryset(self, request):
        return Student.all_objects.all()

    def save_model(self, request, obj, form, change):
        if not obj.admission_number:
            from .services import next_admission_number
            obj.admission_number = next_admission_number()
        super().save_model(request, obj, form, change)
