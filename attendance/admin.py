from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from attendance.models import (
    User, AcademicTerm, Department, Course, Stream, CourseUnit, 
    TeacherProfile, StudentProfile, Book, LibraryRecord, StudentTermFee, 
    FeePaymentTransaction, TimetableBatch, TimetableEntry, 
    AttendanceSession, AttendanceRecord, Hostel, Room, 
    RoomAllocation, DisciplinaryRecord, StaffPaymentRecord
)

# ==================== USER MANAGEMENT ====================

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('System Role Configuration', {'fields': ('role',)}),
    )
    list_display = ('username', 'email', 'role', 'is_staff', 'is_superuser')
    list_filter = ('role', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email')


# ==================== ACADEMIC STRUCTURES ====================

@admin.register(AcademicTerm)
class AcademicTermAdmin(admin.ModelAdmin):
    list_display = ('academic_year', 'term', 'start_date', 'end_date', 'is_current', 'total_days', 'remaining_days')
    list_filter = ('is_current', 'academic_year')
    search_fields = ('academic_year', 'term')


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'department')
    list_filter = ('department',)
    search_fields = ('code', 'name')


@admin.register(Stream)
class StreamAdmin(admin.ModelAdmin):
    list_display = ('name', 'course')
    list_filter = ('course',)
    search_fields = ('name',)


@admin.register(CourseUnit)
class CourseUnitAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'course')
    list_filter = ('course',)
    search_fields = ('code', 'name')


# ==================== PROFILES & CORE LOGS ====================

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('reg_number', 'name', 'course', 'stream')
    list_filter = ('course', 'stream')
    search_fields = ('reg_number', 'name')


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'user')
    search_fields = ('name', 'user__username')


# ==================== FINANCES & PAYROLL ====================

@admin.register(StudentTermFee)
class StudentTermFeeAdmin(admin.ModelAdmin):
    list_display = ('student', 'term', 'total_fees_due', 'total_amount_paid', 'remaining_balance', 'status')
    list_filter = ('term', 'term__academic_year')
    search_fields = ('student__name', 'student__reg_number')


@admin.register(FeePaymentTransaction)
class FeePaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'term_fee_account', 'amount', 'payment_method', 'is_confirmed', 'date_recorded')
    list_filter = ('is_confirmed', 'payment_method', 'date_recorded')
    search_fields = ('reference_number', 'term_fee_account__student__name', 'term_fee_account__student__reg_number')


@admin.register(StaffPaymentRecord)
class StaffPaymentRecordAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'staff', 'amount', 'payment_date', 'payment_method', 'term')
    list_filter = ('payment_method', 'payment_date', 'term')
    search_fields = ('reference_number', 'staff__username', 'description')


# ==================== HOUSING / LODGINGS ====================

class RoomInline(admin.TabularInline):
    model = Room
    extra = 1


@admin.register(Hostel)
class HostelAdmin(admin.ModelAdmin):
    list_display = ('name', 'location')
    inlines = [RoomInline]


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name_or_number', 'hostel', 'capacity')
    list_filter = ('hostel', 'capacity')
    search_fields = ('name_or_number', 'hostel__name')


@admin.register(RoomAllocation)
class RoomAllocationAdmin(admin.ModelAdmin):
    list_display = ('student', 'room', 'term', 'allocated_by', 'allocated_at')
    list_filter = ('term', 'room__hostel')
    search_fields = ('student__name', 'student__reg_number', 'room__name_or_number')


# ==================== TIMETABLE & ATTENDANCE ====================

@admin.register(TimetableBatch)
class TimetableBatchAdmin(admin.ModelAdmin):
    list_display = ('week_start_date', 'term', 'is_active', 'is_revoked', 'uploaded_at')
    list_filter = ('is_active', 'is_revoked', 'term', 'week_start_date')
    search_fields = ('term__academic_year',)


@admin.register(TimetableEntry)
class TimetableEntryAdmin(admin.ModelAdmin):
    list_display = ('day', 'start_time', 'end_time', 'course_unit', 'teacher', 'stream', 'batch')
    list_filter = ('day', 'stream', 'teacher', 'batch')
    search_fields = ('course_unit__name', 'course_unit__code', 'teacher__name')


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ('timetable_entry', 'date_marked', 'teacher_latitude', 'teacher_longitude')
    list_filter = ('date_marked', 'timetable_entry__day')
    search_fields = ('timetable_entry__course_unit__name', 'timetable_entry__teacher__name')


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'session', 'status')
    list_filter = ('status', 'session__date_marked')
    search_fields = ('student__name', 'student__reg_number')


# ==================== INSTITUTIONAL LIBRARY SYSTEM ====================

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'isbn', 'total_copies', 'available_copies')
    search_fields = ('title', 'author', 'isbn')


@admin.register(LibraryRecord)
class LibraryRecordAdmin(admin.ModelAdmin):
    # Fixed to reference database fields exactly as they exist on models.py
    list_display = ('book', 'student', 'teacher', 'issue_date', 'due_date', 'return_date', 'status')
    list_filter = ('status', 'issue_date', 'due_date', 'return_date')
    search_fields = ('book__title', 'student__name', 'student__reg_number', 'teacher__name')


# ==================== DISCIPLINARY MANAGEMENT ====================

@admin.register(DisciplinaryRecord)
class DisciplinaryRecordAdmin(admin.ModelAdmin):
    list_display = ('subject', 'student', 'severity', 'date_logged', 'reported_by', 'term')
    list_filter = ('severity', 'date_logged', 'term')
    search_fields = ('subject', 'student__name', 'student__reg_number', 'details')



from django.contrib import admin
from django.contrib import messages
from .models import ReserveRequest, Book


@admin.register(ReserveRequest)
class ReserveRequestAdmin(admin.ModelAdmin):
    # Columns displayed in the admin list view
    list_display = ('book', 'get_applicant', 'status', 'request_date', 'purpose_notes')
    
    # Filters available on the right sidebar
    list_filter = ('status', 'request_date')
    
    # Search bar across book titles, applicant names, and notes
    search_fields = (
        'book__title', 
        'student__user__first_name', 
        'student__user__last_name',
        'purpose_notes'
    )
    
    # Prevent manual tampering of creation timestamps
    readonly_fields = ('request_date',)
    
    # Default ordering (newest requests first)
    ordering = ('-request_date',)

    # Custom column to show Student or Teacher applicant
    @admin.display(description='Applicant')
    def get_applicant(self, obj):
        if hasattr(obj, 'teacher') and obj.teacher:
            return f"{obj.teacher} (Teacher)"
        elif obj.student:
            return f"{obj.student} (Student)"
        return "N/A"

    # Custom Admin Bulk Actions for quick approval/rejection
    actions = ['approve_requests', 'reject_requests']

    @admin.action(description='Mark selected reserve requests as APPROVED')
    def approve_requests(self, request, queryset):
        updated = queryset.update(status='APPROVED')
        self.message_user(
            request, 
            f"Successfully marked {updated} request(s) as Approved.", 
            messages.SUCCESS
        )

    @admin.action(description='Mark selected reserve requests as REJECTED')
    def reject_requests(self, request, queryset):
        updated = queryset.update(status='REJECTED')
        self.message_user(
            request, 
            f"Successfully marked {updated} request(s) as Rejected.", 
            messages.WARNING
        )