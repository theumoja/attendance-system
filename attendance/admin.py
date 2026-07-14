from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from attendance.models import (
    User, AcademicTerm, Department, Course, Stream, CourseUnit, 
    TeacherProfile, StudentProfile, LibraryRecord, StudentTermFee, 
    FeePaymentTransaction, TimetableBatch, TimetableEntry, 
    AttendanceSession, AttendanceRecord, Hostel, Room, 
    RoomAllocation, DisciplinaryRecord, StaffPaymentRecord
)

# ==================== USER MANAGEMENT ====================

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('System Role Configuration', {'fields': ('role',)}),
    )
    list_display = ('username', 'email', 'role', 'is_staff', 'is_superuser')
    list_filter = ('role', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email')

admin.site.register(User, CustomUserAdmin)


# ==================== ACADEMIC STRUCTURES ====================

class AcademicTermAdmin(admin.ModelAdmin):
    list_display = ('academic_year', 'term', 'start_date', 'end_date', 'is_current')
    list_filter = ('is_current', 'academic_year')
    search_fields = ('academic_year', 'term')

admin.site.register(AcademicTerm, AcademicTermAdmin)
admin.site.register(Department)
admin.site.register(Course)
admin.site.register(Stream)
admin.site.register(CourseUnit)


# ==================== PROFILES & CORE LOGS ====================

class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('reg_number', 'name', 'course', 'stream')
    list_filter = ('course', 'stream')
    search_fields = ('reg_number', 'name')

class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'user')
    search_fields = ('name', 'user__username')

admin.site.register(StudentProfile, StudentProfileAdmin)
admin.site.register(TeacherProfile, TeacherProfileAdmin)


# ==================== FINANCES & PAYROLL ====================

class StudentTermFeeAdmin(admin.ModelAdmin):
    list_display = ('student', 'term', 'total_fees_due', 'total_amount_paid', 'remaining_balance', 'status')
    list_filter = ('term', 'term__academic_year')
    search_fields = ('student__name', 'student__reg_number')

class FeePaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'term_fee_account', 'amount', 'payment_method', 'is_confirmed', 'date_recorded')
    list_filter = ('is_confirmed', 'payment_method', 'date_recorded')
    search_fields = ('reference_number', 'term_fee_account__student__name', 'term_fee_account__student__reg_number')

class StaffPaymentRecordAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'staff', 'amount', 'payment_date', 'payment_method', 'term')
    list_filter = ('payment_method', 'payment_date', 'term')
    search_fields = ('reference_number', 'staff__username', 'description')

admin.site.register(StudentTermFee, StudentTermFeeAdmin)
admin.site.register(FeePaymentTransaction, FeePaymentTransactionAdmin)
admin.site.register(StaffPaymentRecord, StaffPaymentRecordAdmin)


# ==================== HOUSING / LODGINGS ====================

class RoomInline(admin.TabularInline):
    model = Room
    extra = 1

class HostelAdmin(admin.ModelAdmin):
    list_display = ('name', 'location')
    inlines = [RoomInline]

class RoomAllocationAdmin(admin.ModelAdmin):
    list_display = ('student', 'room', 'term', 'allocated_by', 'allocated_at')
    list_filter = ('term', 'room__hostel')
    search_fields = ('student__name', 'student__reg_number', 'room__name_or_number')

admin.site.register(Hostel, HostelAdmin)
admin.site.register(Room)
admin.site.register(RoomAllocation, RoomAllocationAdmin)


# ==================== TIMETABLE & ATTENDANCE ====================

admin.site.register(TimetableBatch)
admin.site.register(TimetableEntry)
admin.site.register(AttendanceSession)
admin.site.register(AttendanceRecord)


# ==================== MISCELLANEOUS SERVICES ====================

class LibraryRecordAdmin(admin.ModelAdmin):
    list_display = ('book_title', 'student', 'date_issued', 'is_returned', 'date_returned', 'term')
    list_filter = ('is_returned', 'date_issued', 'term')
    search_fields = ('book_title', 'student__name', 'student__reg_number')

class DisciplinaryRecordAdmin(admin.ModelAdmin):
    list_display = ('subject', 'student', 'severity', 'date_logged', 'reported_by', 'term')
    list_filter = ('severity', 'date_logged', 'term')
    search_fields = ('subject', 'student__name', 'student__reg_number', 'details')

admin.site.register(LibraryRecord, LibraryRecordAdmin)
admin.site.register(DisciplinaryRecord, DisciplinaryRecordAdmin)