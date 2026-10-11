from django.contrib import admin

from .models import AcademicYear, SchoolClass, Section, Subject, TeachingAssignment

admin.site.register(AcademicYear)
admin.site.register(SchoolClass)
admin.site.register(Subject)


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("school_class", "name", "academic_year", "class_teacher")
    list_filter = ("academic_year", "school_class")


@admin.register(TeachingAssignment)
class TeachingAssignmentAdmin(admin.ModelAdmin):
    list_display = ("teacher", "subject", "section")
