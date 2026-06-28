from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from attendance.models import (
    User, Course, CourseUnit, TeacherProfile, 
    StudentProfile, TimetableBatch, TimetableEntry, 
    AttendanceSession, AttendanceRecord
)

class CustomUserAdmin(UserAdmin):
    # Appends custom fields to the standard user modification layout
    fieldsets = UserAdmin.fieldsets + (
        ('System Role Configuration', {'fields': ('role', 'raw_password_archive')}),
    )
    list_display = ('username', 'email', 'role', 'is_staff', 'is_superuser')
    list_filter = ('role', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email')

# Registering models on the administration site panel
admin.site.register(User, CustomUserAdmin)
admin.site.register(Course)
admin.site.register(CourseUnit)
admin.site.register(TeacherProfile)
admin.site.register(StudentProfile)
admin.site.register(TimetableBatch)
admin.site.register(TimetableEntry)
admin.site.register(AttendanceSession)
admin.site.register(AttendanceRecord)