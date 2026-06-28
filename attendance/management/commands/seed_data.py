import random
from datetime import datetime, timedelta, time
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from attendance.models import (
    User, Course, CourseUnit, TeacherProfile, StudentProfile,
    TimetableBatch, TimetableEntry, AttendanceSession, AttendanceRecord
)

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds the database with test data for all features'

    def handle(self, *args, **options):
        self.stdout.write('Starting seed...')

        # ---------- 1. Create Admin ----------
        admin_user, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@utc.ac.ug',
                'role': User.IS_ADMIN,
                'is_staff': True,
                'is_superuser': True,
            }
        )
        admin_user.set_password('admin123')
        admin_user.save()
        self.stdout.write('Admin created.')

        # ---------- 2. Create Courses and CourseUnits ----------
        courses_data = [
            {'code': 'CIT', 'name': 'Computer Information Technology', 'units': [
                ('CIT101', 'Programming Fundamentals'),
                ('CIT102', 'Database Systems'),
                ('CIT103', 'Networking'),
            ]},
            {'code': 'BBA', 'name': 'Business Administration', 'units': [
                ('BBA201', 'Financial Accounting'),
                ('BBA202', 'Marketing Management'),
                ('BBA203', 'Organizational Behaviour'),
            ]},
            {'code': 'EDU', 'name': 'Education', 'units': [
                ('EDU301', 'Educational Psychology'),
                ('EDU302', 'Curriculum Development'),
                ('EDU303', 'Teaching Methods'),
            ]},
        ]

        for course_info in courses_data:
            course, _ = Course.objects.get_or_create(
                code=course_info['code'],
                defaults={'name': course_info['name']}
            )
            self.stdout.write(f'Course {course.code} created.')
            for unit_code, unit_name in course_info['units']:
                unit, _ = CourseUnit.objects.get_or_create(
                    code=unit_code,
                    defaults={'name': unit_name, 'course': course}
                )
                self.stdout.write(f'  Unit {unit.code} created.')

        # ---------- 3. Create Teachers ----------
        teacher_list = [
            ('Dr. James Muwonge', 'james.muwonge@utc.ac.ug'),
            ('Prof. Grace Nambi', 'grace.nambi@utc.ac.ug'),
            ('Mr. Peter Okello', 'peter.okello@utc.ac.ug'),
            ('Ms. Sarah Kyomugisha', 'sarah.kyomugisha@utc.ac.ug'),
        ]

        teachers = []
        for name, email in teacher_list:
            username = email.split('@')[0]
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'role': User.IS_TEACHER,
                    'raw_password_archive': 'teacher123'
                }
            )
            if created:
                user.set_password('teacher123')
                user.save()
                teacher = TeacherProfile.objects.create(user=user, name=name)
                teachers.append(teacher)
                self.stdout.write(f'Teacher {name} created.')
            else:
                # ensure profile exists
                teacher, _ = TeacherProfile.objects.get_or_create(user=user, defaults={'name': name})
                teachers.append(teacher)
                self.stdout.write(f'Teacher {name} already exists.')

        # ---------- 4. Create Students ----------
        # define courses to assign students
        cit_course = Course.objects.get(code='CIT')
        bba_course = Course.objects.get(code='BBA')
        edu_course = Course.objects.get(code='EDU')

        student_data = [
            ('Aisha Nakato', '2024/001', 'aisha.nakato@utc.ac.ug', cit_course),
            ('Brian Ssali', '2024/002', 'brian.ssali@utc.ac.ug', cit_course),
            ('Christine Akello', '2024/003', 'christine.akello@utc.ac.ug', cit_course),
            ('David Obote', '2024/004', 'david.obote@utc.ac.ug', bba_course),
            ('Eva Mbabazi', '2024/005', 'eva.mbabazi@utc.ac.ug', bba_course),
            ('Frank Opio', '2024/006', 'frank.opio@utc.ac.ug', bba_course),
            ('Grace Auma', '2024/007', 'grace.auma@utc.ac.ug', edu_course),
            ('Henry Ochieng', '2024/008', 'henry.ochieng@utc.ac.ug', edu_course),
            ('Irene Nalongo', '2024/009', 'irene.nalongo@utc.ac.ug', cit_course),
            ('John Kisakye', '2024/010', 'john.kisakye@utc.ac.ug', bba_course),
        ]

        students = []
        for name, reg, email, course in student_data:
            username = reg.replace('/', '_')
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'role': User.IS_STUDENT,
                    'raw_password_archive': 'student123'
                }
            )
            if created:
                user.set_password('student123')
                user.save()
                student = StudentProfile.objects.create(
                    reg_number=reg,
                    user=user,
                    name=name,
                    course=course
                )
                students.append(student)
                self.stdout.write(f'Student {name} ({reg}) created.')
            else:
                # ensure profile exists
                student, _ = StudentProfile.objects.get_or_create(
                    reg_number=reg,
                    defaults={'user': user, 'name': name, 'course': course}
                )
                students.append(student)
                self.stdout.write(f'Student {name} ({reg}) already exists.')

        # ---------- 5. Create Timetable Batch and Entries ----------
        # Use a week starting from next Monday
        today = datetime.now().date()
        days_ahead = 0 - today.weekday()  # 0=Monday, 6=Sunday
        if days_ahead < 0:  # if today is after Monday, go to next week
            days_ahead += 7
        week_start = today + timedelta(days=days_ahead)
        if week_start < today:  # if today is Monday, use today
            week_start = today

        batch, _ = TimetableBatch.objects.get_or_create(
            week_start_date=week_start,
            is_active=True,
            defaults={'is_revoked': False}
        )
        self.stdout.write(f'Timetable batch created for week starting {week_start}.')

        # clear any existing entries for this batch to avoid duplicates
        # (if you want to keep them, use get_or_create with unique constraint)
        # For simplicity, we delete and recreate
        TimetableEntry.objects.filter(batch=batch).delete()

        # Get course units and teachers
        cit101 = CourseUnit.objects.get(code='CIT101')
        cit102 = CourseUnit.objects.get(code='CIT102')
        cit103 = CourseUnit.objects.get(code='CIT103')
        bba201 = CourseUnit.objects.get(code='BBA201')
        bba202 = CourseUnit.objects.get(code='BBA202')
        bba203 = CourseUnit.objects.get(code='BBA203')
        edu301 = CourseUnit.objects.get(code='EDU301')
        edu302 = CourseUnit.objects.get(code='EDU302')
        edu303 = CourseUnit.objects.get(code='EDU303')

        # Map teachers (we have 4 teachers)
        teacher1 = teachers[0]  # Dr. Muwonge
        teacher2 = teachers[1]  # Prof. Nambi
        teacher3 = teachers[2]  # Mr. Okello
        teacher4 = teachers[3]  # Ms. Kyomugisha

        # Define timetable schedule (day, start, end, unit, teacher, class_name)
        schedule = [
            # Monday
            ('MON', '08:30', '10:00', cit101, teacher1, 'Year 1 CIT A'),
            ('MON', '10:15', '11:45', bba201, teacher2, 'Year 1 BBA A'),
            ('MON', '12:00', '13:30', edu301, teacher3, 'Year 1 EDU A'),
            ('MON', '14:00', '15:30', cit102, teacher1, 'Year 2 CIT A'),
            # Tuesday
            ('TUE', '08:30', '10:00', cit103, teacher4, 'Year 2 CIT B'),
            ('TUE', '10:15', '11:45', bba202, teacher2, 'Year 2 BBA A'),
            ('TUE', '12:00', '13:30', edu302, teacher3, 'Year 2 EDU A'),
            ('TUE', '14:00', '15:30', cit101, teacher1, 'Year 1 CIT B'),
            # Wednesday
            ('WED', '08:30', '10:00', bba203, teacher2, 'Year 3 BBA A'),
            ('WED', '10:15', '11:45', edu303, teacher3, 'Year 3 EDU A'),
            ('WED', '12:00', '13:30', cit102, teacher1, 'Year 2 CIT B'),
            ('WED', '14:00', '15:30', cit103, teacher4, 'Year 3 CIT A'),
            # Thursday
            ('THU', '08:30', '10:00', bba201, teacher2, 'Year 1 BBA B'),
            ('THU', '10:15', '11:45', cit101, teacher1, 'Year 1 CIT C'),
            ('THU', '12:00', '13:30', edu301, teacher3, 'Year 1 EDU B'),
            ('THU', '14:00', '15:30', bba202, teacher2, 'Year 2 BBA B'),
            # Friday
            ('FRI', '08:30', '10:00', cit102, teacher1, 'Year 2 CIT C'),
            ('FRI', '10:15', '11:45', edu302, teacher3, 'Year 2 EDU B'),
            ('FRI', '12:00', '13:30', bba203, teacher2, 'Year 3 BBA B'),
            ('FRI', '14:00', '15:30', cit103, teacher4, 'Year 3 CIT B'),
        ]

        for day, start_str, end_str, unit, teacher, class_name in schedule:
            start_time = datetime.strptime(start_str, '%H:%M').time()
            end_time = datetime.strptime(end_str, '%H:%M').time()
            entry = TimetableEntry.objects.create(
                batch=batch,
                day=day,
                start_time=start_time,
                end_time=end_time,
                course_unit=unit,
                teacher=teacher,
                class_name=class_name
            )
            self.stdout.write(f'  Created timetable entry: {day} {start_str}-{end_str} {unit.code}')

        # ---------- 6. Create Attendance Sessions and Records ----------
        # For each timetable entry, create some attendance sessions on recent dates.
        # We'll pick a few entries and generate records for some students.
        entries = TimetableEntry.objects.filter(batch=batch)

        # For each entry, create 1-2 sessions on different dates (simulating multiple lectures)
        for entry in entries:
            # Generate a date within the current week (e.g., Monday to Friday)
            base_date = week_start  # start of week
            # Map day string to weekday offset (0=Monday)
            day_map = {'MON': 0, 'TUE': 1, 'WED': 2, 'THU': 3, 'FRI': 4, 'SAT': 5, 'SUN': 6}
            offset = day_map[entry.day]
            session_date = base_date + timedelta(days=offset)

            # Create 1 or 2 sessions for this entry on different dates (if possible)
            for i in range(random.randint(1, 2)):
                # If we already have a session for this entry on this date, skip to avoid duplicates
                # We'll just create one session per entry for simplicity.
                session_date = session_date  # use same date for now
                # Create session
                session, created = AttendanceSession.objects.get_or_create(
                    timetable_entry=entry,
                    date_marked=session_date,
                    defaults={
                        'teacher_latitude': random.uniform(-1.0, 1.0),
                        'teacher_longitude': random.uniform(30.0, 32.0),
                    }
                )
                if not created:
                    # If session already exists, continue to next entry
                    continue

                # Get students registered for this course unit's course
                # For simplicity, we'll take all students in that course
                course = entry.course_unit.course
                students_in_course = StudentProfile.objects.filter(course=course)

                # Randomly mark 70-90% present
                for student in students_in_course:
                    status = 'PRESENT' if random.random() < 0.8 else 'ABSENT'
                    AttendanceRecord.objects.create(
                        session=session,
                        student=student,
                        status=status
                    )
                self.stdout.write(f'  Created attendance session for {entry.course_unit.code} on {session_date} with {students_in_course.count()} records.')

        self.stdout.write(self.style.SUCCESS('Seed completed successfully!'))