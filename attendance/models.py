from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser): #[cite: 1]
    IS_ADMIN = 'ADMIN' #[cite: 1]
    IS_TEACHER = 'TEACHER' #[cite: 1]
    IS_STUDENT = 'STUDENT' #[cite: 1]
    
    ROLE_CHOICES = [ #[cite: 1]
        (IS_ADMIN, 'Admin'), #[cite: 1]
        (IS_TEACHER, 'Teacher/Lecturer'), #[cite: 1]
        (IS_STUDENT, 'Student'), #[cite: 1]
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=IS_STUDENT) #[cite: 1]
    raw_password_archive = models.CharField(max_length=128, blank=True, null=True) #[cite: 1]

class Department(models.Model):
    """ADDED: Department structural grouping to allow multiple courses to pin to a department."""
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

class Course(models.Model): #[cite: 1]
    code = models.CharField(max_length=20, primary_key=True) #[cite: 1]
    name = models.CharField(max_length=255) #[cite: 1]
    # UPDATED: Linked relation allowing multiple courses to be pinned under a department
    department = models.ForeignKey(
        Department, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='courses'
    )

    def __str__(self): #[cite: 1]
        return f"{self.code} - {self.name}" #[cite: 1]

class Stream(models.Model): #[cite: 1]
    """ADDED: Relational Stream groupings linked directly to a parent course program.""" #[cite: 1]
    name = models.CharField(max_length=100) #[cite: 1]
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='streams') #[cite: 1]

    def __str__(self): #[cite: 1]
        return self.name #[cite: 1]

class CourseUnit(models.Model): #[cite: 1]
    code = models.CharField(max_length=20, primary_key=True) #[cite: 1]
    name = models.CharField(max_length=255) #[cite: 1]
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='units') #[cite: 1]

    def __str__(self): #[cite: 1]
        return f"{self.code} - {self.name}" #[cite: 1]

class TeacherProfile(models.Model): #[cite: 1]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile') #[cite: 1]
    name = models.CharField(max_length=255) #[cite: 1]
    courses = models.ManyToManyField('Course', blank=True, related_name='teachers') #[cite: 1]

    def __str__(self): #[cite: 1]
        return self.name #[cite: 1]

class StudentProfile(models.Model): #[cite: 1]
    reg_number = models.CharField(max_length=50, primary_key=True) #[cite: 1]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile') #[cite: 1]
    name = models.CharField(max_length=255) #[cite: 1]
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='students') #[cite: 1]
    stream = models.ForeignKey(Stream, on_delete=models.CASCADE, related_name='students') #[cite: 1]

    def __str__(self): #[cite: 1]
        return f"{self.reg_number} - {self.name}" #[cite: 1]

class TimetableBatch(models.Model): #[cite: 1]
    uploaded_at = models.DateTimeField(auto_now_add=True) #[cite: 1]
    week_start_date = models.DateField() #[cite: 1]
    is_active = models.BooleanField(default=True) #[cite: 1]
    is_revoked = models.BooleanField(default=False) #[cite: 1]

class TimetableEntry(models.Model): #[cite: 1]
    DAYS_OF_WEEK = [ #[cite: 1]
        ('MON', 'Monday'), ('TUE', 'Tuesday'), ('WED', 'Wednesday'), #[cite: 1]
        ('THU', 'Thursday'), ('FRI', 'Friday'), ('SAT', 'Saturday'), ('SUN', 'Sunday') #[cite: 1]
    ]
    batch = models.ForeignKey(TimetableBatch, on_delete=models.CASCADE, related_name='entries') #[cite: 1]
    day = models.CharField(max_length=3, choices=DAYS_OF_WEEK) #[cite: 1]
    start_time = models.TimeField() #[cite: 1]
    end_time = models.TimeField() #[cite: 1]
    course_unit = models.ForeignKey(CourseUnit, on_delete=models.CASCADE) #[cite: 1]
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE) #[cite: 1]
    stream = models.ForeignKey(Stream, on_delete=models.CASCADE, related_name='entries') #[cite: 1]

class AttendanceSession(models.Model): #[cite: 1]
    timetable_entry = models.ForeignKey(TimetableEntry, on_delete=models.CASCADE) #[cite: 1]
    date_marked = models.DateField(auto_now_add=True) #[cite: 1]
    teacher_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True) #[cite: 1]
    teacher_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True) #[cite: 1]

class AttendanceRecord(models.Model): #[cite: 1]
    STATUS_CHOICES = [('PRESENT', 'Present'), ('ABSENT', 'Absent')] #[cite: 1]
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name='records') #[cite: 1]
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE) #[cite: 1]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES) #[cite: 1]