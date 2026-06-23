from django.contrib import admin
from .models import (
    Course,
    CourseUnit,
    TeacherAssignment,
    StudentUnitEnrollment,     # new
    AttendanceRecord,
    Profile,
)

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'description']
    search_fields = ['code', 'name']

@admin.register(CourseUnit)
class CourseUnitAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'course']
    list_filter = ['course']
    search_fields = ['code', 'name']

@admin.register(TeacherAssignment)
class TeacherAssignmentAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'course']
    list_filter = ['course']
    search_fields = ['teacher__username']

@admin.register(StudentUnitEnrollment)
class StudentUnitEnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'course_unit', 'is_approved']
    list_filter = ['is_approved', 'course_unit__course']
    search_fields = ['student__username', 'course_unit__code']

@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ['student', 'course_unit', 'date', 'is_present', 'marked_by']
    list_filter = ['date', 'is_present', 'course_unit__course']
    search_fields = ['student__username']

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'is_approved']
    list_filter = ['role', 'is_approved']
    search_fields = ['user__username']
    filter_horizontal = ['applied_courses', 'applied_units']   # updated field names