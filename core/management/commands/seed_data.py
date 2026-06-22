from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from core.models import (
    Course,
    CourseUnit,
    Profile,
    Enrollment,
    TeacherAssignment,
    AttendanceRecord,
)
from django.utils import timezone


class Command(BaseCommand):
    help = 'Seed database with sample courses, units, users, and an attendance record'

    def handle(self, *args, **options):
        # ----- Create groups if not exist -----
        student_group, _ = Group.objects.get_or_create(name='Student')
        teacher_group, _ = Group.objects.get_or_create(name='Teacher')
        admin_group, _ = Group.objects.get_or_create(name='Admin')

        # ----- Create sample courses -----
        cs101, created = Course.objects.get_or_create(
            code='CS101',
            defaults={
                'name': 'Introduction to Computing',
                'description': 'Basics of computer science'
            }
        )
        math201, created = Course.objects.get_or_create(
            code='MATH201',
            defaults={
                'name': 'Calculus II',
                'description': 'Advanced differentiation & integration'
            }
        )
        phys101, created = Course.objects.get_or_create(
            code='PHYS101',
            defaults={
                'name': 'Physics for Engineers',
                'description': 'Mechanics, thermodynamics, waves'
            }
        )

        # ----- Create sample course units -----
        units = [
            ('CS101', 'CS101-01', 'Fundamentals of Programming'),
            ('CS101', 'CS101-02', 'Data Structures & Algorithms'),
            ('MATH201', 'MATH201-01', 'Multivariable Calculus'),
            ('MATH201', 'MATH201-02', 'Differential Equations'),
            ('PHYS101', 'PHYS101-01', 'Classical Mechanics'),
            ('PHYS101', 'PHYS101-02', 'Thermodynamics'),
        ]
        course_map = {'CS101': cs101, 'MATH201': math201, 'PHYS101': phys101}
        unit_objects = {}
        for course_code, unit_code, unit_name in units:
            course = course_map[course_code]
            unit_obj, _ = CourseUnit.objects.get_or_create(
                course=course,
                code=unit_code,
                defaults={'name': unit_name}
            )
            unit_objects[unit_code] = unit_obj

        # ----- Create sample users -----
        user_data = [
            ('alice', 'password', 'Student', ['CS101', 'MATH201']),
            ('bob', 'password', 'Student', ['PHYS101']),
            ('dr_smith', 'password', 'Teacher', ['CS101', 'MATH201']),
            ('dr_jones', 'password', 'Teacher', ['PHYS101']),
            ('admin1', 'password', 'Admin', []),
        ]

        for username, pwd, role, course_codes in user_data:
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.set_password(pwd)
                user.save()
            # Update or create profile
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.role = role
            profile.is_approved = True  # auto‑approve for testing
            profile.save()
            # Set courses for Student/Teacher
            if role in ('Student', 'Teacher'):
                profile.courses.set([course_map[code] for code in course_codes])
            else:
                profile.courses.clear()
            # Assign user to appropriate group
            user.groups.clear()
            if role == 'Student':
                user.groups.add(student_group)
            elif role == 'Teacher':
                user.groups.add(teacher_group)
            elif role == 'Admin':
                user.groups.add(admin_group)

            # Create enrolments / teacher assignments
            if role == 'Student':
                for code in course_codes:
                    Enrollment.objects.get_or_create(student=user, course=course_map[code])
            elif role == 'Teacher':
                for code in course_codes:
                    TeacherAssignment.objects.get_or_create(teacher=user, course=course_map[code])

        # ----- Create a sample attendance record -----
        alice = User.objects.get(username='alice')
        unit = unit_objects['CS101-01']
        today = timezone.now().date()
        AttendanceRecord.objects.get_or_create(
            student=alice,
            course_unit=unit,
            date=today,
            defaults={
                'is_present': True,
                'teacher_gps_lat': 0.3136,
                'teacher_gps_lon': 32.5811,
                'marked_by': User.objects.get(username='dr_smith')
            }
        )

        self.stdout.write(self.style.SUCCESS('Sample data seeded successfully!'))