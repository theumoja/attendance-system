import random
from datetime import datetime, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from attendance.models import (
    User, Department, Course, CourseUnit, Stream, TeacherProfile, StudentProfile,
    AcademicTerm, StudentTermFee, FeePaymentTransaction, Book, LibraryRecord,
    ReserveRequest, TimetableBatch, TimetableEntry, AttendanceSession, AttendanceRecord,
    Hostel, Room, RoomAllocation, DisciplinaryRecord, StaffPaymentRecord
)

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds the database with a full roster, attendance records, realistic library catalog, lodgings, and disciplinary sector data.'

    def handle(self, *args, **options):
        self.stdout.write('Starting comprehensive database seed...')

        # ---------- 0. Clear existing academic terms to avoid overlap conflicts ----------
        AcademicTerm.objects.all().delete()
        self.stdout.write('Existing academic terms purged.')

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
        self.stdout.write('Admin user verified.')

        # ---------- 2. Create Specialized Staff Roles ----------
        # Accountant
        accountant_user, created = User.objects.get_or_create(
            username='sam_accountant',
            defaults={'email': 'sam.accountant@utc.ac.ug', 'role': User.IS_ACCOUNTANT}
        )
        if created:
            accountant_user.set_password('accountant123')
            accountant_user.save()

        # Librarian
        librarian_user, created = User.objects.get_or_create(
            username='jane_librarian',
            defaults={'email': 'jane.librarian@utc.ac.ug', 'role': User.IS_LIBRARIAN}
        )
        if created:
            librarian_user.set_password('librarian123')
            librarian_user.save()

        # Warden (Lodgings)
        warden_user, created = User.objects.get_or_create(
            username='mary_warden',
            defaults={'email': 'mary.warden@utc.ac.ug', 'role': User.IS_WARDEN}
        )
        if created:
            warden_user.set_password('warden123')
            warden_user.save()
            
        self.stdout.write('Specialized institutional staff profiles initialized.')

        # ---------- 3. Create Academic Terms ----------
        today_date = timezone.localdate()
       
        term_1, _ = AcademicTerm.objects.get_or_create(
            academic_year='2025/2026',
            term='TERM_1',
            defaults={
                'start_date': today_date - timedelta(days=270),
                'end_date': today_date - timedelta(days=180),
                'is_current': False
            }
        )
        term_2, _ = AcademicTerm.objects.get_or_create(
            academic_year='2025/2026',
            term='TERM_2',
            defaults={
                'start_date': today_date - timedelta(days=170),
                'end_date': today_date - timedelta(days=100),
                'is_current': False
            }
        )
        current_term, _ = AcademicTerm.objects.get_or_create(
            academic_year='2025/2026',
            term='TERM_3',
            defaults={
                'start_date': today_date - timedelta(days=90),
                'end_date': today_date + timedelta(days=30),
                'is_current': True
            }
        )
        self.stdout.write('Institutional operational terms mapped.')

        # ---------- 4. Create Departments ----------
        dept_cit, _ = Department.objects.get_or_create(name='Computing and Information Technology')
        dept_biz, _ = Department.objects.get_or_create(name='Business Studies')
        dept_edu, _ = Department.objects.get_or_create(name='Education')
        self.stdout.write('Core departments verified.')

        # ---------- 5. Create Courses and CourseUnits ----------
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
            course, _ = Course.objects.get_or_create(
                code=course_info['code'],
                defaults={'name': course_info['name'], 'department': course_info['department']}
            )
            for unit_code, unit_name in course_info['units']:
                CourseUnit.objects.get_or_create(
                    code=unit_code,
                    defaults={'name': unit_name, 'course': course}
                )
        self.stdout.write('Academic courses and modules indexed.')

        # ---------- 6. Create Streams for Courses ----------
        unique_streams_data = [
            ('CIT', 'Year 1 CIT A'), ('CIT', 'Year 1 CIT B'),
            ('BBA', 'Year 1 BBA A'), ('BBA', 'Year 1 BBA B'),
            ('EDU', 'Year 1 EDU A'), ('EDU', 'Year 1 EDU B')
        ]

        all_streams = []
        for course_code, stream_name in unique_streams_data:
            course_obj = Course.objects.get(code=course_code)
            stream_obj, _ = Stream.objects.get_or_create(name=stream_name, course=course_obj)
            all_streams.append(stream_obj)

        # ---------- 7. Create Teachers ----------
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
                defaults={'email': email, 'role': User.IS_TEACHER}
            )
            if created:
                user.set_password('teacher123')
                user.save()
            teacher, _ = TeacherProfile.objects.get_or_create(user=user, defaults={'name': name})
            teachers.append(teacher)

        # ---------- 8. Create Hostels and Rooms (Lodgings) ----------
        hostel_m, _ = Hostel.objects.get_or_create(name='Albert Nile Hall', location='North Campus Zone')
        hostel_f, _ = Hostel.objects.get_or_create(name='Victoria Hall', location='East Campus Zone')
       
        all_rooms = []
        for room_num in ['A1', 'A2', 'B1', 'B2', 'C1']:
            r1, _ = Room.objects.get_or_create(hostel=hostel_m, name_or_number=room_num, defaults={'capacity': 4})
            r2, _ = Room.objects.get_or_create(hostel=hostel_f, name_or_number=room_num, defaults={'capacity': 4})
            all_rooms.extend([r1, r2])
        self.stdout.write('Hostel infrastructure and room distribution maps generated.')

        # ---------- 9. Researched Academic Books Catalog ----------
        researched_books = [
            # --- Computing & Information Technology ---
            {
                'title': 'Introduction to Algorithms (4th Edition)',
                'author': 'Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest, Clifford Stein',
                'isbn': '9780262046305',
                'total_copies': 5,
                'available_copies': 2,
                'is_reserve': True  # High demand standard reference
            },
            {
                'title': 'Database System Concepts (7th Edition)',
                'author': 'Abraham Silberschatz, Henry F. Korth, S. Sudarshan',
                'isbn': '9781260515046',
                'total_copies': 8,
                'available_copies': 6,
                'is_reserve': False
            },
            {
                'title': 'Computer Networking: A Top-Down Approach',
                'author': 'James Kurose, Keith Ross',
                'isbn': '9780136681557',
                'total_copies': 6,
                'available_copies': 4,
                'is_reserve': False
            },
            {
                'title': 'Clean Code: A Handbook of Agile Software Craftsmanship',
                'author': 'Robert C. Martin',
                'isbn': '9780132350884',
                'total_copies': 4,
                'available_copies': 1,
                'is_reserve': False
            },
            {
                'title': 'Operating System Concepts',
                'author': 'Abraham Silberschatz, Peter B. Galvin, Greg Gagne',
                'isbn': '9781119800361',
                'total_copies': 3,
                'available_copies': 1,
                'is_reserve': True
            },

            # --- Business Administration & Management ---
            {
                'title': 'Financial Accounting (12th Edition)',
                'author': 'Walter T. Harrison, Charles T. Horngren, C. William Thomas',
                'isbn': '9780134727691',
                'total_copies': 10,
                'available_copies': 7,
                'is_reserve': False
            },
            {
                'title': 'Principles of Marketing (18th Edition)',
                'author': 'Philip Kotler, Gary Armstrong',
                'isbn': '9780135766606',
                'total_copies': 8,
                'available_copies': 5,
                'is_reserve': False
            },
            {
                'title': 'Organizational Behavior (18th Edition)',
                'author': 'Stephen P. Robbins, Timothy A. Judge',
                'isbn': '9780134729664',
                'total_copies': 4,
                'available_copies': 2,
                'is_reserve': True
            },
            {
                'title': 'Corporate Finance: Theory and Practice',
                'author': 'Jonathan Berk, Peter DeMarzo',
                'isbn': '9780134640846',
                'total_copies': 6,
                'available_copies': 3,
                'is_reserve': False
            },

            # --- Education & Humanities ---
            {
                'title': 'Educational Psychology (14th Edition)',
                'author': 'Anita Woolfolk',
                'isbn': '9780134774329',
                'total_copies': 7,
                'available_copies': 4,
                'is_reserve': False
            },
            {
                'title': 'Curriculum: Foundations, Principles, and Issues',
                'author': 'Allan C. Ornstein, Francis P. Hunkins',
                'isbn': '9780134013503',
                'total_copies': 5,
                'available_copies': 2,
                'is_reserve': True
            },
            {
                'title': 'Methods for Effective Teaching: Meeting the Needs of All Students',
                'author': 'Paul R. Burden, David M. Byrd',
                'isbn': '9780134801933',
                'total_copies': 6,
                'available_copies': 5,
                'is_reserve': False
            }
        ]

        book_objects = []
        general_book_objects = []
        reserve_book_objects = []

        for b_data in researched_books:
            book, _ = Book.objects.get_or_create(
                isbn=b_data['isbn'],
                defaults={
                    'title': b_data['title'],
                    'author': b_data['author'],
                    'total_copies': b_data['total_copies'],
                    'available_copies': b_data['available_copies'],
                    'is_reserve': b_data['is_reserve']
                }
            )
            book_objects.append(book)
            if book.is_reserve:
                reserve_book_objects.append(book)
            else:
                general_book_objects.append(book)

        self.stdout.write(f'Cataloged {len(book_objects)} authentic academic titles across departments.')

        # ---------- 10. Dynamic Student Roster & Sector Records Seeding ----------
        self.stdout.write('Generating student cohorts along with library, lodging, and financial records...')
       
        first_names = ['Musa', 'Abel', 'Ivan', 'Emmanuel', 'Sarah', 'Joy', 'Harriet', 'Brenda', 'Derrick', 'Charles']
        last_names = ['Otim', 'Okello', 'Mukasa', 'Kato', 'Wasswa', 'Opio', 'Mwenge', 'Kigozi', 'Nsubuga', 'Mugisha']

        student_counter = 100
        all_students = []

        for stream in all_streams:
            num_students = random.randint(12, 15)
            for _ in range(num_students):
                student_counter += 1
                reg_number = f"2024/{student_counter:03d}"
                full_name = f"{random.choice(first_names)} {random.choice(last_names)}"
                email = f"{full_name.lower().replace(' ', '.')}@utc.ac.ug"

                user, created = User.objects.get_or_create(
                    username=reg_number.replace('/', '_'),
                    defaults={'email': email, 'role': User.IS_STUDENT}
                )
                if created:
                    user.set_password('student123')
                    user.save()

                student_prof, _ = StudentProfile.objects.get_or_create(
                    reg_number=reg_number,
                    defaults={'user': user, 'name': full_name, 'course': stream.course, 'stream': stream}
                )
                all_students.append(student_prof)

                # --- Seed Accountant Data (Student Term Fees) ---
                base_fees = Decimal('1500000.00')
                paid_amount = Decimal(random.choice(['0.00', '500000.00', '1000000.00', '1500000.00']))
               
                fee_acc, _ = StudentTermFee.objects.get_or_create(
                    student=student_prof,
                    term=current_term,
                    defaults={'total_fees_due': base_fees, 'total_amount_paid': paid_amount}
                )

                if paid_amount > 0:
                    FeePaymentTransaction.objects.get_or_create(
                        term_fee_account=fee_acc,
                        amount=paid_amount,
                        reference_number=f"TXN-{student_counter}-{random.randint(1000, 9999)}",
                        defaults={
                            'payment_method': random.choice(['BANK_DEPOSIT', 'MOBILE_MONEY', 'CASH']),
                            'is_confirmed': True,
                            'date_confirmed': timezone.now(),
                            'processed_by': accountant_user
                        }
                    )

                # --- Seed Lodgings Data (multi-term) ---
                if random.random() < 0.40:
                    historical_room = random.choice(all_rooms)
                    if historical_room.allocations.filter(term=term_2).count() < historical_room.capacity:
                        RoomAllocation.objects.get_or_create(
                            student=student_prof,
                            term=term_2,
                            defaults={'room': historical_room, 'allocated_by': warden_user}
                        )

                if random.random() < 0.50:
                    assigned_room = random.choice(all_rooms)
                    current_occupancy = assigned_room.allocations.filter(term=current_term).count()
                    if current_occupancy < assigned_room.capacity:
                        RoomAllocation.objects.get_or_create(
                            student=student_prof,
                            term=current_term, 
                            defaults={'room': assigned_room, 'allocated_by': warden_user}
                        )

                # --- Seed General Library Checkout Records ---
                if random.random() < 0.35 and general_book_objects:
                    book = random.choice(general_book_objects)
                    issued = random.choice([True, False])
                    issue_date = timezone.now().date() - timedelta(days=random.randint(5, 20))
                    
                    if book.available_copies < 1:
                        book.available_copies = random.randint(1, 3)
                        book.save()

                    LibraryRecord.objects.create(
                        student=student_prof,
                        book=book,
                        issue_date=issue_date,
                        due_date=issue_date + timedelta(days=14),
                        return_date=issue_date + timedelta(days=random.randint(1, 12)) if issued else None,
                        status='RETURNED' if issued else 'ISSUED',
                        remarks=random.choice(['', 'Good condition', 'Slight wear', 'Standard checkout'])
                    )

                # --- Seed Reserve Section Applications ---
                if random.random() < 0.15 and reserve_book_objects:
                    reserve_book = random.choice(reserve_book_objects)
                    req_status = random.choice(['PENDING', 'APPROVED', 'DECLINED'])
                    ReserveRequest.objects.get_or_create(
                        student=student_prof,
                        book=reserve_book,
                        defaults={
                            'status': req_status,
                            'request_date': timezone.now() - timedelta(days=random.randint(1, 10))
                        }
                    )

        # --- Seed Staff Payout Logs ---
        for teacher in teachers:
            StaffPaymentRecord.objects.get_or_create(
                reference_number=f"SAL-{teacher.user.id}-{random.randint(10000, 99999)}",
                defaults={
                    'staff': teacher.user,
                    'amount': Decimal('2800000.00'),
                    'payment_date': today_date - timedelta(days=10),
                    'payment_method': 'BANK_TRANSFER',
                    'description': 'Monthly Institutional Teaching Compensation',
                    'term': current_term,
                    'processed_by': accountant_user
                }
            )

        # --- Seed Disciplinary Records ---
        disciplinary_targets = random.sample(all_students, k=min(len(all_students), 5))
        infractions = [
            ("Examination Malpractice", "Caught with unauthorized summarized notes during the mid-term tests.", "SEVERE"),
            ("Hostel Property Damage", "Accidental destruction of common room structural fittings during evening matches.", "MILD"),
            ("Curfew Breach", "Repeatedly arriving at the residential halls past official gate closure limits.", "MILD"),
            ("Library Book Defacement", "Tearing out core reference material pages from structural textbooks.", "VERY_SEVERE")
        ]
       
        for idx, target_student in enumerate(disciplinary_targets):
            infraction = infractions[idx % len(infractions)]
            DisciplinaryRecord.objects.create(
                student=target_student,
                subject=infraction[0],
                details=infraction[1],
                severity=infraction[2],
                reported_by=random.choice(teachers).user,
                term=current_term
            )

        self.stdout.write('Financial ledger matrix, housing logs, and active library operations established.')

        # ---------- 11. MULTI-WEEK TIMETABLE & HISTORICAL ATTENDANCE ----------
        self.stdout.write('Generating structural attendance line history (Past 12 Weeks)...')
       
        today = datetime.now().date()
        current_week_start = today - timedelta(days=today.weekday())
       
        schedule_blueprint = [
            ('MON', '08:30', '10:00', 'CIT101', teachers[0], 'Year 1 CIT A'),
            ('MON', '10:15', '11:45', 'BBA201', teachers[1], 'Year 1 BBA A'),
            ('MON', '12:00', '13:30', 'EDU301', teachers[2], 'Year 1 EDU A'),
            ('TUE', '08:30', '10:00', 'CIT103', teachers[3], 'Year 1 CIT A'),
            ('TUE', '10:15', '11:45', 'BBA202', teachers[1], 'Year 1 BBA A'),
            ('WED', '08:30', '10:00', 'BBA203', teachers[1], 'Year 1 BBA A'),
            ('WED', '10:15', '11:45', 'EDU303', teachers[2], 'Year 1 EDU A'),
            ('THU', '08:30', '10:00', 'BBA201', teachers[1], 'Year 1 BBA B'),
            ('THU', '10:15', '11:45', 'CIT101', teachers[0], 'Year 1 CIT B'),
            ('FRI', '08:30', '10:00', 'CIT102', teachers[0], 'Year 1 CIT B'),
        ]

        cu_map = {cu.code: cu for cu in CourseUnit.objects.all()}
        day_index_offset = {'MON': 0, 'TUE': 1, 'WED': 2, 'THU': 3, 'FRI': 4}

        for weeks_ago in range(12, -1, -1):
            target_week_start = current_week_start - timedelta(weeks=weeks_ago)
            is_active_week = (weeks_ago == 0)

            TimetableBatch.objects.filter(week_start_date=target_week_start).delete()

            batch = TimetableBatch.objects.create(
                week_start_date=target_week_start,
                is_active=is_active_week,
                is_revoked=False,
                term=current_term
            )

            for day_code, s_time, e_time, cu_code, teacher_obj, stream_name in schedule_blueprint:
                start_t = datetime.strptime(s_time, '%H:%M').time()
                end_t = datetime.strptime(e_time, '%H:%M').time()
                stream_obj = Stream.objects.get(name=stream_name)
               
                entry = TimetableEntry.objects.create(
                    batch=batch,
                    day=day_code,
                    start_time=start_t,
                    end_time=end_t,
                    course_unit=cu_map[cu_code],
                    teacher=teacher_obj,
                    stream=stream_obj
                )

                session_date = target_week_start + timedelta(days=day_index_offset[day_code])
                if session_date > today:
                    continue

                session = AttendanceSession.objects.create(
                    timetable_entry=entry,
                    teacher_latitude=random.uniform(-0.1, 0.1),
                    teacher_longitude=random.uniform(32.4, 32.6)
                )
                AttendanceSession.objects.filter(id=session.id).update(date_marked=session_date)

                presence_probability = 0.84
                if day_code == 'FRI':
                    presence_probability -= 0.10
                if weeks_ago in [5, 6]:
                    presence_probability -= 0.08

                presence_probability = max(0.50, min(0.98, presence_probability))
                target_students = StudentProfile.objects.filter(stream=entry.stream)
                records_pool = []
               
                for student in target_students:
                    computed_status = 'PRESENT' if random.random() < presence_probability else 'ABSENT'
                    records_pool.append(
                        AttendanceRecord(session=session, student=student, status=computed_status)
                    )
               
                AttendanceRecord.objects.bulk_create(records_pool)

        self.stdout.write(self.style.SUCCESS('Seed completed successfully! Academic, Administrative and specialized roles seed data is now fully active.'))