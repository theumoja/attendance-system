from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    IS_ADMIN = 'ADMIN'
    IS_TEACHER = 'TEACHER'
    IS_STUDENT = 'STUDENT'
    
    ROLE_CHOICES = [
        (IS_ADMIN, 'Admin'),
        (IS_TEACHER, 'Teacher/Lecturer'),
        (IS_STUDENT, 'Student'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=IS_STUDENT)
    raw_password_archive = models.CharField(max_length=128, blank=True, null=True)

class Course(models.Model):
    code = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.code} - {self.name}"

class Stream(models.Model):
    """ADDED: Relational Stream groupings linked directly to a parent course program."""
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
    stream = models.ForeignKey(Stream, on_delete=models.CASCADE, related_name='students') # UPDATED TO FOREIGN KEY

    def __str__(self):
        return f"{self.reg_number} - {self.name}"

class TimetableBatch(models.Model):
    uploaded_at = models.DateTimeField(auto_now_add=True)
    week_start_date = models.DateField()
    is_active = models.BooleanField(default=True)
    is_revoked = models.BooleanField(default=False)

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
    stream = models.ForeignKey(Stream, on_delete=models.CASCADE, related_name='entries') # MODIFIED FROM class_name STRING

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