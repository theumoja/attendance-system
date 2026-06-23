# core/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

# ---------- Course & CourseUnit (unchanged) ----------
class Course(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.code} - {self.name}"

class CourseUnit(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='units')
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20)

    class Meta:
        unique_together = ['course', 'code']

    def __str__(self):
        return f"{self.course.code} / {self.code} - {self.name}"

# ---------- Teacher Assignment (unchanged) ----------
class TeacherAssignment(models.Model):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'groups__name': 'Teacher'})
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    class Meta:
        unique_together = ['teacher', 'course']

    def __str__(self):
        return f"{self.teacher.username} teaches {self.course.code}"

# core/models.py

class StudentUnitEnrollment(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REVOKED', 'Revoked'),
        ('REAPPLIED', 'Reapplied'),
    ]
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'groups__name': 'Student'})
    course_unit = models.ForeignKey(CourseUnit, on_delete=models.CASCADE, related_name='enrollments')
    is_approved = models.BooleanField(default=False)   # True only when status is APPROVED
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')

    class Meta:
        unique_together = ['student', 'course_unit']

    def __str__(self):
        return f"{self.student.username} -> {self.course_unit.code} ({self.get_status_display()})"

# ---------- Attendance Record (unchanged) ----------
class AttendanceRecord(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendance_records')
    course_unit = models.ForeignKey(CourseUnit, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField(default=timezone.now)
    is_present = models.BooleanField(default=False)
    teacher_gps_lat = models.FloatField(null=True, blank=True)
    teacher_gps_lon = models.FloatField(null=True, blank=True)
    marked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='marked_attendances')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['student', 'course_unit', 'date']

    def __str__(self):
        status = "Present" if self.is_present else "Absent"
        return f"{self.student.username} - {self.course_unit.code} - {self.date} ({status})"

# ---------- Profile (slightly modified: remove courses field) ----------
class Profile(models.Model):
    ROLE_CHOICES = [
        ('Student', 'Student'),
        ('Teacher', 'Teacher'),
        ('Admin', 'Admin'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='Student')
    is_approved = models.BooleanField(default=False)
    # For teacher: apply for whole courses
    applied_courses = models.ManyToManyField(Course, blank=True, help_text="Courses you wish to teach (Teacher only)")
    # For student: apply for specific course units
    applied_units = models.ManyToManyField(CourseUnit, blank=True, help_text="Course units you wish to enroll in (Student only)")

    def __str__(self):
        return f"{self.user.username} ({self.role})"

# Signals
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()