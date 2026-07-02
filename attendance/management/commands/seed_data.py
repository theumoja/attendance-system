import random
from datetime import datetime, timedelta, time
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from attendance.models import (
    User, Department, Course, CourseUnit, Stream, TeacherProfile, StudentProfile,
    TimetableBatch, TimetableEntry, AttendanceSession, AttendanceRecord
)

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds the database with test data for all features including departments'

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

        # ---------- 2. Create Departments ----------
        self.stdout.write('Creating Departments...')
        dept_cit, _ = Department.objects.get_or_create(name='Computing and Information Technology')
        dept_biz, _ = Department.objects.get_or_create(name='Business Studies')
        dept_edu, _ = Department.objects.get_or_create(name='Education')
        self.stdout.write('Departments created.')

        # ---------- 3. Create Courses and CourseUnits ----------
        courses_data = [
            {
                'code': 'CIT', 
                'name': 'Computer Information Technology', 
                'department': dept_cit,
                'units': [
                    ('CIT101', 'Programming Fundamentals'),
                    ('CIT102', 'Database Systems'),
                    ('CIT103', 'Networking'),
                ]
            },
            {
                'code': 'BBA', 
                'name': 'Business Administration', 
                'department': dept_biz,
                'units': [
                    ('BBA201', 'Financial Accounting'),
                    ('BBA202', 'Marketing Management'),
                    ('BBA203', 'Organizational Behaviour'),
                ]
            },
            {
                'code': 'EDU', 
                'name': 'Education', 
                'department': dept_edu,
                'units': [
                    ('EDU301', 'Educational Psychology'),
                    ('EDU302', 'Curriculum Development'),
                    ('EDU303', 'Teaching Methods'),
                ]
            },
        ]

        for course_info in courses_data:
            course, created = Course.objects.get_or_create(
                code=course_info['code'],
                defaults={
                    'name': course_info['name'],
                    'department': course_info['department']
                }
            )
            if not created:
                course.name = course_info['name']
                course.department = course_info['department']
                course.save()
                
            self.stdout.write(f'Course {course.code} assigned to Department: "{course.department.name}".')
            
            for unit_code, unit_name in course_info['units']:
                unit, _ = CourseUnit.objects.get_or_create(
                    code=unit_code,
                    defaults={'name': unit_name, 'course': course}
                )
                self.stdout.write(f'  Unit {unit.code} created.')

        # ---------- 4. Create Streams for Courses ----------
        unique_streams_data = [
            ('CIT', 'Year 1 CIT A'), ('CIT', 'Year 1 CIT B'), ('CIT', 'Year 1 CIT C'),
            ('CIT', 'Year 2 CIT A'), ('CIT', 'Year 2 CIT B'), ('CIT', 'Year 2 CIT C'),
            ('CIT', 'Year 3 CIT A'), ('CIT', 'Year 3 CIT B'),
            ('BBA', 'Year 1 BBA A'), ('BBA', 'Year 1 BBA B'),
            ('BBA', 'Year 2 BBA A'), ('BBA', 'Year 2 BBA B'),
            ('BBA', 'Year 3 BBA A'), ('BBA', 'Year 3 BBA B'),
            ('EDU', 'Year 1 EDU A'), ('EDU', 'Year 1 EDU B'),
            ('EDU', 'Year 2 EDU A'), ('EDU', 'Year 2 EDU B'),
            ('EDU', 'Year 3 EDU A')
        ]

        streams_dict = {}
        for course_code, stream_name in unique_streams_data:
            course_obj = Course.objects.get(code=course_code)
            stream_obj, _ = Stream.objects.get_or_create(name=stream_name, course=course_obj)
            streams_dict[stream_name] = stream_obj
            self.stdout.write(f'  Stream "{stream_name}" registered for Course {course_code}.')

        # ---------- 5. Create Teachers ----------
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
                teacher, _ = TeacherProfile.objects.get_or_create(user=user, defaults={'name': name})
                teachers.append(teacher)
                self.stdout.write(f'Teacher {name} already exists.')

        # ---------- 6. Create Students ----------
        cit_course = Course.objects.get(code='CIT')
        bba_course = Course.objects.get(code='BBA')
        edu_course = Course.objects.get(code='EDU')

        student_data = [
            ('Aisha Nakato', '2024/001', 'aisha.nakato@utc.ac.ug', cit_course, 'Year 1 CIT A'),
            ('Brian Ssali', '2024/002', 'brian.ssali@utc.ac.ug', cit_course, 'Year 1 CIT A'),
            ('Christine Akello', '2024/003', 'christine.akello@utc.ac.ug', cit_course, 'Year 1 CIT B'),
            ('David Obote', '2024/004', 'david.obote@utc.ac.ug', bba_course, 'Year 1 BBA A'),
            ('Eva Mbabazi', '2024/005', 'eva.mbabazi@utc.ac.ug', bba_course, 'Year 1 BBA A'),
            ('Frank Opio', '2024/006', 'frank.opio@utc.ac.ug', bba_course, 'Year 2 BBA A'),
            ('Grace Auma', '2024/007', 'grace.auma@utc.ac.ug', edu_course, 'Year 1 EDU A'),
            ('Henry Ochieng', '2024/008', 'henry.ochieng@utc.ac.ug', edu_course, 'Year 1 EDU B'),
            ('Irene Nalongo', '2024/009', 'irene.nalongo@utc.ac.ug', cit_course, 'Year 2 CIT A'),
            ('John Kisakye', '2024/010', 'john.kisakye@utc.ac.ug', bba_course, 'Year 3 BBA A'),
        ]

        students = []
        for name, reg, email, course, stream_name in student_data:
            username = reg.replace('/', '_')
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'role': User.IS_STUDENT,
                    'raw_password_archive': 'student123'
                }
            )
            
            stream_obj = streams_dict[stream_name]
            
            if created:
                user.set_password('student123')
                user.save()
                student = StudentProfile.objects.create(
                    reg_number=reg,
                    user=user,
                    name=name,
                    course=course,
                    stream=stream_obj
                )
                students.append(student)
                self.stdout.write(f'Student {name} ({reg}) created in stream {stream_name}.')
            else:
                student, _ = StudentProfile.objects.get_or_create(
                    reg_number=reg,
                    defaults={'user': user, 'name': name, 'course': course, 'stream': stream_obj}
                )
                student.stream = stream_obj
                student.save()
                students.append(student)
                self.stdout.write(f'Student {name} ({reg}) already exists.')

        # ---------- 7. Create Timetable Batch and Entries ----------
        today = datetime.now().date()
        days_ahead = 0 - today.weekday()
        if days_ahead < 0:
            days_ahead += 7
        week_start = today + timedelta(days=days_ahead)
        if week_start < today:
            week_start = today

        batch, _ = TimetableBatch.objects.get_or_create(
            week_start_date=week_start,
            is_active=True,
            defaults={'is_revoked': False}
        )
        self.stdout.write(f'Timetable batch created for week starting {week_start}.')

        TimetableEntry.objects.filter(batch=batch).delete()

        cit101 = CourseUnit.objects.get(code='CIT101')
        cit102 = CourseUnit.objects.get(code='CIT102')
        cit103 = CourseUnit.objects.get(code='CIT103')
        bba201 = CourseUnit.objects.get(code='BBA201')
        bba202 = CourseUnit.objects.get(code='BBA202')
        bba203 = CourseUnit.objects.get(code='BBA203')
        edu301 = CourseUnit.objects.get(code='EDU301')
        edu302 = CourseUnit.objects.get(code='EDU302')
        edu303 = CourseUnit.objects.get(code='EDU303')

        teacher1 = teachers[0]
        teacher2 = teachers[1]
        teacher3 = teachers[2]
        teacher4 = teachers[3]

        schedule = [
            ('MON', '08:30', '10:00', cit101, teacher1, 'Year 1 CIT A'),
            ('MON', '10:15', '11:45', bba201, teacher2, 'Year 1 BBA A'),
            ('MON', '12:00', '13:30', edu301, teacher3, 'Year 1 EDU A'),
            ('MON', '14:00', '15:30', cit102, teacher1, 'Year 2 CIT A'),
            ('TUE', '08:30', '10:00', cit103, teacher4, 'Year 2 CIT B'),
            ('TUE', '10:15', '11:45', bba202, teacher2, 'Year 2 BBA A'),
            ('TUE', '12:00', '13:30', edu302, teacher3, 'Year 2 EDU A'),
            ('TUE', '14:00', '15:30', cit101, teacher1, 'Year 1 CIT B'),
            ('WED', '08:30', '10:00', bba203, teacher2, 'Year 3 BBA A'),
            ('WED', '10:15', '11:45', edu303, teacher3, 'Year 3 EDU A'),
            ('WED', '12:00', '13:30', cit102, teacher1, 'Year 2 CIT B'),
            ('WED', '14:00', '15:30', cit103, teacher4, 'Year 3 CIT A'),
            ('THU', '08:30', '10:00', bba201, teacher2, 'Year 1 BBA B'),
            ('THU', '10:15', '11:45', cit101, teacher1, 'Year 1 CIT C'),
            ('THU', '12:00', '13:30', edu301, teacher3, 'Year 1 EDU B'),
            ('THU', '14:00', '15:30', bba202, teacher2, 'Year 2 BBA B'),
            ('FRI', '08:30', '10:00', cit102, teacher1, 'Year 2 CIT C'),
            ('FRI', '10:15', '11:45', edu302, teacher3, 'Year 2 EDU B'),
            ('FRI', '12:00', '13:30', bba203, teacher2, 'Year 3 BBA B'),
            ('FRI', '14:00', '15:30', cit103, teacher4, 'Year 3 CIT B'),
        ]

        for day, start_str, end_str, unit, teacher, stream_name in schedule:
            start_time = datetime.strptime(start_str, '%H:%M').time()
            end_time = datetime.strptime(end_str, '%H:%M').time()
            
            stream_obj = streams_dict[stream_name]
            
            TimetableEntry.objects.create(
                batch=batch,
                day=day,
                start_time=start_time,
                end_time=end_time,
                course_unit=unit,
                teacher=teacher,
                stream=stream_obj
            )
            self.stdout.write(f'  Created timetable entry: {day} {start_str}-{end_str} {unit.code} ({stream_name})')

        # ---------- 8. Create Attendance Sessions and Records ----------
        entries = TimetableEntry.objects.filter(batch=batch)

        for entry in entries:
            base_date = week_start
            day_map = {'MON': 0, 'TUE': 1, 'WED': 2, 'THU': 3, 'FRI': 4, 'SAT': 5, 'SUN': 6}
            offset = day_map[entry.day]
            session_date = base_date + timedelta(days=offset)

            for i in range(random.randint(1, 2)):
                session, created = AttendanceSession.objects.get_or_create(
                    timetable_entry=entry,
                    date_marked=session_date,
                    defaults={
                        'teacher_latitude': random.uniform(-1.0, 1.0),
                        'teacher_longitude': random.uniform(30.0, 32.0),
                    }
                )
                if not created:
                    continue

                students_in_stream = StudentProfile.objects.filter(stream=entry.stream)

                for student in students_in_stream:
                    status = 'PRESENT' if random.random() < 0.8 else 'ABSENT'
                    AttendanceRecord.objects.create(
                        session=session,
                        student=student,
                        status=status
                    )
                self.stdout.write(f'  Created attendance session for {entry.course_unit.code} ({entry.stream.name}) on {session_date} with {students_in_stream.count()} records.')

        self.stdout.write(self.style.SUCCESS('Seed completed successfully!'))