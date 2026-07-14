from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal

class User(AbstractUser):
    IS_ADMIN = 'ADMIN'
    IS_TEACHER = 'TEACHER'
    IS_STUDENT = 'STUDENT'
    IS_WARDEN = 'WARDEN'
    IS_LIBRARIAN = 'LIBRARIAN'
    IS_ACCOUNTANT = 'ACCOUNTANT'
    
    ROLE_CHOICES = [
        (IS_ADMIN, 'Admin'),
        (IS_TEACHER, 'Teacher/Lecturer'),
        (IS_STUDENT, 'Student'),
        (IS_WARDEN, 'Warden'),
        (IS_LIBRARIAN, 'Librarian'),
        (IS_ACCOUNTANT, 'Accountant'),
    ]
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default=IS_STUDENT)


# ==================== ENHANCED: ACADEMIC PERIOD TRACKING ====================

class AcademicTerm(models.Model):
    """
    Defines the structural Term block for the entire institution.
    Enforces dates validation and overlap preventions for administrators.
    """
    TERM_CHOICES = [
        ('TERM_1', 'Term 1'),
        ('TERM_2', 'Term 2'),
        ('TERM_3', 'Term 3'),
        ('RECESS', 'Recess Term'),
    ]
    
    academic_year = models.CharField(max_length=9, help_text="E.g., 2025/2026, 2026/2027")
    term = models.CharField(max_length=10, choices=TERM_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False, help_text="Designates if this is the active operational term")

    class Meta:
        unique_together = ('academic_year', 'term')
        verbose_name = "Academic Term"
        verbose_name_plural = "Academic Terms"

    def clean(self):
        """
        Enforces strict administrative rules regarding operational start and end windows.
        """
        super().clean()
        
        if self.start_date and self.end_date:
            # Rule 1: End date must not precede the start date
            if self.start_date >= self.end_date:
                raise ValidationError({
                    'end_date': "The designated terminal end date must fall after the operational start date."
                })

            # Rule 2: Prevent date overlaps across different academic term entries
            overlapping_terms = AcademicTerm.objects.filter(
                start_date__lt=self.end_date,
                end_date__gt=self.start_date
            )
            
            if self.pk:
                overlapping_terms = overlapping_terms.exclude(pk=self.pk)
                
            if overlapping_terms.exists():
                clashing = overlapping_terms.first()
                raise ValidationError(
                    f"The selected schedule overlaps with an existing term block: {clashing} "
                    f"({clashing.start_date} to {clashing.end_date}). Please adjust the dates."
                )

    def save(self, *args, **kwargs):
        # Triggers full_clean before database entry to execute clean validation logic safely
        self.full_clean()
        
        # Enforce that only one term can be marked active/current at a time
        if self.is_current:
            AcademicTerm.objects.filter(is_current=True).exclude(pk=self.pk).update(is_current=False)
            
        super().save(*args, **kwargs)

    @property
    def total_days(self):
        """Calculates total lifespan duration of this specific term block."""
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days
        return 0

    @property
    def remaining_days(self):
        """Tracks the exact time windows left before term completion."""
        today = timezone.localdate()
        if self.end_date < today:
            return 0
        if self.start_date > today:
            return self.total_days
        return (self.end_date - today).days

    def __str__(self):
        return f"{self.academic_year} - {self.get_term_display()}"


# =======================================================================

class Department(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class Course(models.Model):
    code = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=255)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='courses')

    def __str__(self):
        return f"{self.code} - {self.name}"


class Stream(models.Model):
    name = models.CharField(max_length=100)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='streams')

    def __str__(self):
        return self.name


class CourseUnit(models.Model):
    code = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=255)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='units')

    def __str__(self):
        return f"{self.code} - {self.name}"


class TeacherProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    name = models.CharField(max_length=255)
    courses = models.ManyToManyField('Course', blank=True, related_name='teachers')

    def __str__(self):
        return self.name


class StudentProfile(models.Model):
    reg_number = models.CharField(max_length=50, primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    name = models.CharField(max_length=255)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='students')
    stream = models.ForeignKey(Stream, on_delete=models.CASCADE, related_name='students')

    def __str__(self):
        return f"{self.reg_number} - {self.name}"


class LibraryRecord(models.Model):
    student = models.ForeignKey('StudentProfile', on_delete=models.CASCADE, related_name='borrowed_books')
    book_title = models.CharField(max_length=255)
    date_issued = models.DateField(default=timezone.now)
    is_returned = models.BooleanField(default=False)
    date_returned = models.DateField(null=True, blank=True)
    issued_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, limit_choices_to={'role': 'LIBRARIAN'})
    term = models.ForeignKey(AcademicTerm, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        status = "Returned" if self.is_returned else "Active"
        return f"{self.book_title} -> {self.student.name} ({status})"


# ==================== PER-TERM FEE ACCOUNTING ====================

class StudentTermFee(models.Model):
    """
    Tracks an explicit financial ledger for each student *per term*.
    """
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='term_fees')
    term = models.ForeignKey(AcademicTerm, on_delete=models.CASCADE, related_name='student_fees')
    total_fees_due = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    class Meta:
        unique_together = ('student', 'term')
        verbose_name = "Student Term Fee Balance"
        verbose_name_plural = "Student Term Fee Balances"

    @property
    def remaining_balance(self):
        return self.total_fees_due - self.total_amount_paid

    @property
    def status(self):
        if self.remaining_balance <= 0:
            return "Cleared"
        elif self.total_amount_paid > 0:
            return "Partially Paid"
        return "Unpaid"

    def __str__(self):
        return f"{self.student.name} ({self.term}) - Balance: {self.remaining_balance}"


class FeePaymentTransaction(models.Model):
    PAYMENT_METHODS = [
        ('BANK_DEPOSIT', 'Direct Bank Deposit'),
        ('MOBILE_MONEY', 'Mobile Money Transfer'),
        ('CASH', 'Cash Desk Payment'),
    ]

    term_fee_account = models.ForeignKey(StudentTermFee, on_delete=models.CASCADE, related_name='transactions', null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='BANK_DEPOSIT')
    reference_number = models.CharField(max_length=100, unique=True, help_text="Bank slip transaction number or mobile money TxID")
    is_confirmed = models.BooleanField(default=False)
    date_recorded = models.DateTimeField(auto_now_add=True)
    date_confirmed = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, limit_choices_to={'role': 'ACCOUNTANT'})

    def __str__(self):
        status = "Confirmed" if self.is_confirmed else "Pending Verification"
        student_name = self.term_fee_account.student.name if self.term_fee_account else "Unknown"
        return f"Tx: {self.reference_number} | {student_name} ({status})"


# ===========================================================================

class TimetableBatch(models.Model):
    uploaded_at = models.DateTimeField(auto_now_add=True)
    week_start_date = models.DateField()
    is_active = models.BooleanField(default=True)
    is_revoked = models.BooleanField(default=False)
    term = models.ForeignKey(AcademicTerm, on_delete=models.CASCADE, related_name='timetable_batches', null=True)


class TimetableEntry(models.Model):
    DAYS_OF_WEEK = [
        ('MON', 'Monday'), ('TUE', 'Tuesday'), ('WED', 'Wednesday'),
        ('THU', 'Thursday'), ('FRI', 'Friday'), ('SAT', 'Saturday'), ('SUN', 'Sunday')
    ]
    batch = models.ForeignKey(TimetableBatch, on_delete=models.CASCADE, related_name='entries')
    day = models.CharField(max_length=3, choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    course_unit = models.ForeignKey(CourseUnit, on_delete=models.CASCADE)
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE)
    stream = models.ForeignKey(Stream, on_delete=models.CASCADE, related_name='entries')


class AttendanceSession(models.Model):
    timetable_entry = models.ForeignKey(TimetableEntry, on_delete=models.CASCADE)
    date_marked = models.DateField(auto_now_add=True)
    teacher_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    teacher_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)


class AttendanceRecord(models.Model):
    STATUS_CHOICES = [('PRESENT', 'Present'), ('ABSENT', 'Absent')]
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name='records')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)


class Hostel(models.Model):
    name = models.CharField(max_length=255, unique=True)
    location = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name


class Room(models.Model):
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name='rooms')
    name_or_number = models.CharField(max_length=50)
    capacity = models.PositiveIntegerField(default=4)

    def __str__(self):
        return f"{self.hostel.name} - Room {self.name_or_number}"


class RoomAllocation(models.Model):
    # CHANGE: Changed from OneToOneField to ForeignKey to allow historical/multi-term allocations
    student = models.ForeignKey(
        StudentProfile, 
        on_delete=models.CASCADE, 
        related_name='room_allocations'
    )
    room = models.ForeignKey(
        Room, 
        on_delete=models.CASCADE, 
        related_name='allocations'
    )
    allocated_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        limit_choices_to={'role': 'WARDEN'}
    )
    allocated_at = models.DateTimeField(auto_now=True)
    term = models.ForeignKey(
        AcademicTerm, 
        on_delete=models.CASCADE, 
        related_name='room_allocations', 
        null=True
    )

    class Meta:
        # NEW: Enforces that a student can only be assigned to ONE room during a specific academic term
        unique_together = ('student', 'term')

    def __str__(self):
        return f"{self.student.name} -> {self.room} ({self.term})"

class DisciplinaryRecord(models.Model):
    SEVERITY_LEVELS = [
        ('MILD', 'Mild Case'),
        ('SEVERE', 'Severe Breach'),
        ('VERY_SEVERE', 'Very Severe / Critical'),
    ]

    student = models.ForeignKey('StudentProfile', on_delete=models.CASCADE, related_name='disciplinary_logs')
    subject = models.CharField(max_length=255, help_text="Brief tagline of the complaint or incident summary")
    details = models.TextField(help_text="Detailed narrative of what transpired")
    severity = models.CharField(max_length=15, choices=SEVERITY_LEVELS, default='MILD')
    date_logged = models.DateTimeField(auto_now_add=True)
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reported_incidents')
    term = models.ForeignKey(AcademicTerm, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.subject} - Student: {self.student.name}"


# ==================== STAFF PAYMENTS PER TERM ====================

class StaffPaymentRecord(models.Model):
    PAYMENT_METHODS = [
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('MOBILE_MONEY', 'Mobile Money Transfer'),
        ('CASH', 'Cash Desk Payout'),
    ]

    staff = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='staff_payments',
        limit_choices_to={'role__in': ['ADMIN', 'TEACHER', 'WARDEN', 'LIBRARIAN', 'ACCOUNTANT']}
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField(default=timezone.now)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='BANK_TRANSFER')
    reference_number = models.CharField(max_length=100, unique=True, help_text="Salary slip bank reference or voucher transaction number ID")
    description = models.TextField(blank=True, help_text="E.g., June Basic Salary, Overtime Allowance")
    
    term = models.ForeignKey(
        AcademicTerm, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='staff_payouts',
        help_text="The operational term under which this payout budget falls"
    )
    
    processed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='processed_staff_salaries', 
        limit_choices_to={'role': 'ACCOUNTANT'}
    )

    def __str__(self):
        term_str = f" | {self.term}" if self.term else ""
        return f"Staff Pay: {self.reference_number} | {self.staff.username} ({self.amount}){term_str}"