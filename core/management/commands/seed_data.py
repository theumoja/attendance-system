# core/management/commands/seed_data.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from core.models import (
    Course,
    CourseUnit,
    Profile,
    StudentUnitEnrollment,
    TeacherAssignment,
    AttendanceRecord,
)
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Seed database with sample courses, units, users, and varied GPS attendance records'

    def handle(self, *args, **options):
        # ----- Create groups if not exist -----
        student_group, _ = Group.objects.get_or_create(name='Student')
        teacher_group, _ = Group.objects.get_or_create(name='Teacher')
        admin_group, _ = Group.objects.get_or_create(name='Admin')

        # ----- Create sample courses -----
        cs101, _ = Course.objects.get_or_create(
            code='CS101',
            defaults={
                'name': 'Introduction to Computing',
                'description': 'Basics of computer science'
            }
        )
        math201, _ = Course.objects.get_or_create(
            code='MATH201',
            defaults={
                'name': 'Calculus II',
                'description': 'Advanced differentiation & integration'
            }
        )
        phys101, _ = Course.objects.get_or_create(
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

            profile, _ = Profile.objects.get_or_create(user=user)
            profile.role = role
            profile.is_approved = True          # auto‑approve for testing
            profile.save()

            # Clear any previous M2M relations
            profile.applied_courses.clear()
            profile.applied_units.clear()

            # Assign to proper group
            user.groups.clear()
            if role == 'Student':
                user.groups.add(student_group)
                applied_courses = [course_map[code] for code in course_codes]
                units_to_apply = CourseUnit.objects.filter(course__in=applied_courses)
                profile.applied_units.set(units_to_apply)
                
                for unit in units_to_apply:
                    StudentUnitEnrollment.objects.get_or_create(
                        student=user,
                        course_unit=unit,
                        defaults={'is_approved': True}
                    )
            elif role == 'Teacher':
                user.groups.add(teacher_group)
                applied_courses = [course_map[code] for code in course_codes]
                profile.applied_courses.set(applied_courses)
                
                for course in applied_courses:
                    TeacherAssignment.objects.get_or_create(teacher=user, course=course)
            elif role == 'Admin':
                user.groups.add(admin_group)

        # ----- MODIFIED: Create realistic varied historical GPS data streams -----
        alice_user = User.objects.get(username='alice')
        bob_user = User.objects.get(username='bob')
        teacher_smith = User.objects.get(username='dr_smith')
        teacher_jones = User.objects.get(username='dr_jones')
        
        today = timezone.now().date()

        # Collection matrix covering distinct lecture rooms and campuses
        historical_attendance_records = [
            # Day 1: Today - Regular Class Session
            {
                'student': alice_user,
                'course_unit': unit_objects['CS101-01'],
                'date': today,
                'is_present': True,
                'teacher_gps_lat': 0.3349,  # Main Campus - Lecture Block A
                'teacher_gps_lon': 32.5684,
                'marked_by': teacher_smith
            },
            {
                'student': bob_user,
                'course_unit': unit_objects['PHYS101-01'],
                'date': today,
                'is_present': True,
                'teacher_gps_lat': 0.3323,  # Tech Labs - Wing B
                'teacher_gps_lon': 32.5702,
                'marked_by': teacher_jones
            },
            
            # Day 2: Yesterday - Midweek Track Session
            {
                'student': alice_user,
                'course_unit': unit_objects['CS101-02'],
                'date': today - timedelta(days=1),
                'is_present': True,
                'teacher_gps_lat': 0.3361,  # Computing Innovation Center
                'teacher_gps_lon': 32.5658,
                'marked_by': teacher_smith
            },
            {
                'student': bob_user,
                'course_unit': unit_objects['PHYS101-02'],
                'date': today - timedelta(days=1),
                'is_present': False,  # Absent, preserving model integrity defaults
                'teacher_gps_lat': 0.3345,
                'teacher_gps_lon': 32.5670,
                'marked_by': teacher_jones
            },

            # Day 3: Two Days Ago - Morning Lectures
            {
                'student': alice_user,
                'course_unit': unit_objects['MATH201-01'],
                'date': today - timedelta(days=2),
                'is_present': True,
                'teacher_gps_lat': 0.3136,  # Regional Extension Hub
                'teacher_gps_lon': 32.5811,
                'marked_by': teacher_smith
            },
            {
                'student': bob_user,
                'course_unit': unit_objects['PHYS101-01'],
                'date': today - timedelta(days=2),
                'is_present': True,
                'teacher_gps_lat': 0.3338,  # Science Faculty Quad
                'teacher_gps_lon': 32.5662,
                'marked_by': teacher_jones
            }
        ]

        # Iteratively seed the records into the database
        records_count = 0
        for data in historical_attendance_records:
            _, created = AttendanceRecord.objects.get_or_create(
                student=data['student'],
                course_unit=data['course_unit'],
                date=data['date'],
                defaults={
                    'is_present': data['is_present'],
                    'teacher_gps_lat': data['teacher_gps_lat'],
                    'teacher_gps_lon': data['teacher_gps_lon'],
                    'marked_by': data['marked_by']
                }
            )
            if created:
                records_count += 1

        self.stdout.write(
            self.style.SUCCESS(f'Sample data seeded successfully! Created {records_count} new historical GPS entries.')
        )