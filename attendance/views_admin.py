import csv
import io
import json
import secrets
from datetime import datetime, timedelta

from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q

from attendance.models import (
    User, Course, CourseUnit, TeacherProfile, StudentProfile,
    TimetableBatch, TimetableEntry, AttendanceRecord
)


def generate_secure_password():
    return secrets.token_urlsafe(8)


@login_required
def admin_dashboard(request):
    if request.user.role != User.IS_ADMIN:
        return HttpResponse("Unauthorized", status=403)

    total_courses = Course.objects.count()
    total_teachers = TeacherProfile.objects.count()
    total_students = StudentProfile.objects.count()
    total_present = AttendanceRecord.objects.filter(status='PRESENT').count()
    total_records = AttendanceRecord.objects.count()
    overall_rate = round((total_present / total_records) * 100, 2) if total_records > 0 else 0

    # Per‑teacher attendance (for chart)
    teacher_stats = []
    teachers = TeacherProfile.objects.all()
    for t in teachers:
        present = AttendanceRecord.objects.filter(
            session__timetable_entry__teacher=t,
            status='PRESENT'
        ).count()
        total = AttendanceRecord.objects.filter(
            session__timetable_entry__teacher=t
        ).count()
        rate = round((present / total) * 100, 2) if total > 0 else 0
        teacher_stats.append({'name': t.name, 'rate': rate})
    teacher_names = [ts['name'] for ts in teacher_stats]
    teacher_rates = [ts['rate'] for ts in teacher_stats]

    # Per‑student attendance (top 10)
    student_stats = StudentProfile.objects.annotate(
        present=Count('attendancerecord', filter=Q(attendancerecord__status='PRESENT')),
        total=Count('attendancerecord')
    ).order_by('-total')[:10]
    student_labels = [s.name for s in student_stats]
    student_present = [s.present for s in student_stats]
    student_absent = [s.total - s.present for s in student_stats]

    context = {
        'total_courses': total_courses,
        'total_teachers': total_teachers,
        'total_students': total_students,
        'overall_rate': overall_rate,
        'teacher_names': json.dumps(teacher_names),
        'teacher_rates': json.dumps(teacher_rates),
        'student_labels': json.dumps(student_labels),
        'student_present': json.dumps(student_present),
        'student_absent': json.dumps(student_absent),
    }
    return render(request, 'attendance/admin_dashboard.html', context)


@login_required
@transaction.atomic
def bulk_upload_courses(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        decoded_file = csv_file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        reader = csv.reader(io_string, delimiter=',')
        next(reader, None)  # skip header

        for row in reader:
            if len(row) >= 4:
                c_code, c_name, cu_code, cu_name = row[0].strip(), row[1].strip(), row[2].strip(), row[3].strip()
                course, _ = Course.objects.get_or_create(code=c_code, defaults={'name': c_name})
                CourseUnit.objects.get_or_create(code=cu_code, defaults={'name': cu_name, 'course': course})
        return redirect('attendance:admin_dashboard')
    return render(request, 'attendance/upload_courses.html')


@login_required
@transaction.atomic
def bulk_upload_teachers(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        decoded_file = csv_file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        reader = csv.reader(io_string, delimiter=',')
        next(reader, None)

        for row in reader:
            if len(row) >= 2:
                name, email = row[0].strip(), row[1].strip()
                username = email.split('@')[0]
                password = generate_secure_password()

                user, created = User.objects.get_or_create(email=email, defaults={
                    'username': username,
                    'role': User.IS_TEACHER,
                    'raw_password_archive': password
                })
                if created:
                    user.set_password(password)
                    user.save()
                    TeacherProfile.objects.create(user=user, name=name)
        return redirect('attendance:export_credentials', role_type='teachers')
    return render(request, 'attendance/upload_teachers.html')


@login_required
@transaction.atomic
def bulk_upload_students(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        decoded_file = csv_file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        reader = csv.reader(io_string, delimiter=',')
        next(reader, None)

        for row in reader:
            if len(row) >= 4:
                name, reg_num, email, course_code = row[0].strip(), row[1].strip(), row[2].strip(), row[3].strip()
                try:
                    course = Course.objects.get(code=course_code)
                    password = generate_secure_password()
                    user, created = User.objects.get_or_create(email=email, defaults={
                        'username': reg_num.replace('/', '_'),
                        'role': User.IS_STUDENT,
                        'raw_password_archive': password
                    })
                    if created:
                        user.set_password(password)
                        user.save()
                        StudentProfile.objects.create(user=user, reg_number=reg_num, name=name, course=course)
                except Course.DoesNotExist:
                    continue
        return redirect('attendance:export_credentials', role_type='students')
    return render(request, 'attendance/upload_students.html')


@login_required
def export_credentials(request, role_type):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{role_type}_credentials.csv"'
    writer = csv.writer(response)
    writer.writerow(['Identifier/Email', 'Name', 'Generated Password'])

    if role_type == 'teachers':
        profiles = TeacherProfile.objects.all()
        for p in profiles:
            writer.writerow([p.user.email, p.name, p.user.raw_password_archive])
    elif role_type == 'students':
        profiles = StudentProfile.objects.all()
        for p in profiles:
            writer.writerow([p.reg_number, p.name, p.user.raw_password_archive])

    return response


@login_required
@transaction.atomic
def upload_timetable(request):
    if request.method == 'POST':
        use_last = request.POST.get('use_last_one') == 'true'

        if use_last:
            last_batch = TimetableBatch.objects.filter(is_revoked=False).order_by('-uploaded_at')[:1]
            if last_batch:
                TimetableBatch.objects.filter(is_active=True).update(is_active=False)
                new_batch = TimetableBatch.objects.create(
                    week_start_date=datetime.now().date(), is_active=True
                )
                for entry in last_batch[0].entries.all():
                    TimetableEntry.objects.create(
                        batch=new_batch,
                        day=entry.day,
                        start_time=entry.start_time,
                        end_time=entry.end_time,
                        course_unit=entry.course_unit,
                        teacher=entry.teacher,
                        class_name=entry.class_name
                    )
                return redirect('attendance:admin_dashboard')

        csv_file = request.FILES.get('csv_file')
        if csv_file:
            TimetableBatch.objects.filter(is_active=True).update(is_active=False)
            new_batch = TimetableBatch.objects.create(
                week_start_date=datetime.now().date(), is_active=True
            )
            decoded_file = csv_file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.reader(io_string, delimiter=',')
            next(reader, None)

            for row in reader:
                if len(row) >= 6:
                    day, start_t, end_t, cu_code, teacher_email, class_name = row
                    try:
                        cu = CourseUnit.objects.get(code=cu_code.strip())
                        teacher = TeacherProfile.objects.get(user__email=teacher_email.strip())
                        TimetableEntry.objects.create(
                            batch=new_batch,
                            day=day.strip(),
                            start_time=datetime.strptime(start_t.strip(), '%H:%M').time(),
                            end_time=datetime.strptime(end_t.strip(), '%H:%M').time(),
                            course_unit=cu,
                            teacher=teacher,
                            class_name=class_name.strip()
                        )
                    except (CourseUnit.DoesNotExist, TeacherProfile.DoesNotExist, ValueError):
                        continue
            return redirect('attendance:admin_dashboard')

    return render(request, 'attendance/upload_timetable.html')


def download_template(request, template_type):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{template_type}_template.csv"'

    if template_type == 'courses':
        content = "course_code,course_name,course_unit_code,course_unit_name\nC001,Computer Science,CS101,Programming Basics\nC001,Computer Science,CS102,Data Structures"
    elif template_type == 'teachers':
        content = "teachers_name,email\nJohn Doe,john@example.com"
    elif template_type == 'students':
        content = "students_name,registration_number,email,course\nAlice Smith,2024/001,alice@example.com,C001"
    elif template_type == 'timetable':
        content = "day,start_time,end_time,course_unit_code,teacher_email,class_name\nMON,08:30,10:00,CS101,john@example.com,Class A"
    else:
        content = ""

    response.write(content)
    return response



from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill

@login_required
def export_credentials(request, role_type):
    # Create Excel workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Credentials"

    headers = ['Identifier/Email', 'Name', 'Generated Password']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')
        cell.fill = PatternFill(start_color='d3d3d3', end_color='d3d3d3', fill_type='solid')

    row_num = 2
    if role_type == 'teachers':
        profiles = TeacherProfile.objects.select_related('user').all()
        for p in profiles:
            ws.cell(row=row_num, column=1, value=p.user.email)
            ws.cell(row=row_num, column=2, value=p.name)
            ws.cell(row=row_num, column=3, value=p.user.raw_password_archive)
            row_num += 1
    elif role_type == 'students':
        profiles = StudentProfile.objects.select_related('user').all()
        for p in profiles:
            ws.cell(row=row_num, column=1, value=p.reg_number)
            ws.cell(row=row_num, column=2, value=p.name)
            ws.cell(row=row_num, column=3, value=p.user.raw_password_archive)
            row_num += 1

    # Auto-width
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        ws.column_dimensions[column].width = adjusted_width

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{role_type}_credentials.xlsx"'
    wb.save(response)
    return response