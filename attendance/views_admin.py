import csv
import io
import json
import secrets
from datetime import datetime, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, Http404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q

from attendance.models import (
    User, Course, CourseUnit, TeacherProfile, StudentProfile,
    TimetableBatch, TimetableEntry, AttendanceRecord
)


def generate_secure_password():
    return secrets.token_urlsafe(8)


# =========================================================================
# 1. TEACHERS MANAGEMENT
# =========================================================================

@login_required
@transaction.atomic
def manage_teachers(request):
    if request.user.role != User.IS_ADMIN:
        return HttpResponse("Unauthorized", status=403)

    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Single Add Teacher
        if action == 'single' or ('name' in request.POST and 'email' in request.POST):
            name = request.POST.get('name', '').strip()
            email = request.POST.get('email', '').strip()
            course_codes = request.POST.getlist('courses')
            
            if name and email:
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
                    teacher = TeacherProfile.objects.create(user=user, name=name)
                    if course_codes:
                        teacher.courses.set(Course.objects.filter(code__in=course_codes))
                    messages.success(request, f"Teacher account created for {name}.")
                else:
                    messages.warning(request, "A user with this email already exists.")
            return redirect('attendance:manage_teachers')

        # Bulk Upload CSV
        elif action == 'bulk' and request.FILES.get('csv_file'):
            csv_file = request.FILES['csv_file']
            decoded_file = csv_file.read().decode('utf-8')
            reader = csv.reader(io.StringIO(decoded_file), delimiter=',')
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

    teachers = TeacherProfile.objects.select_related('user').prefetch_related('courses').all()
    all_courses = Course.objects.all()
    return render(request, 'attendance/manage_teachers.html', {
        'teachers': teachers, 
        'all_courses': all_courses,
        'active_courses_list': all_courses
    })


@login_required
@transaction.atomic
def edit_teacher(request, pk):
    if request.user.role != User.IS_ADMIN:
        return HttpResponse("Unauthorized", status=403)
    
    teacher = get_object_or_404(TeacherProfile, pk=pk)
    if request.method == 'POST':
        teacher.name = request.POST.get('name', '').strip()
        teacher.user.email = request.POST.get('email', '').strip()
        teacher.user.save()
        teacher.save()
        
        course_codes = request.POST.getlist('courses')
        teacher.courses.set(Course.objects.filter(code__in=course_codes))
        messages.success(request, "Teacher record updated successfully.")
        return redirect('attendance:manage_teachers')
    
    all_courses = Course.objects.all()
    return render(request, 'attendance/edit_teacher.html', {'teacher': teacher, 'all_courses': all_courses})


@login_required
@transaction.atomic
def delete_teacher(request, pk):
    if request.user.role != User.IS_ADMIN:
        return HttpResponse("Unauthorized", status=403)
    
    teacher = get_object_or_404(TeacherProfile, pk=pk)
    user = teacher.user
    teacher.delete()
    user.delete()
    messages.success(request, "Teacher record permanently deleted.")
    return redirect('attendance:manage_teachers')


# =========================================================================
# 2. STUDENTS MANAGEMENT
# =========================================================================

@login_required
@transaction.atomic
def manage_students(request):
    if request.user.role != User.IS_ADMIN:
        return HttpResponse("Unauthorized", status=403)

    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Ensure single add handler catches the payload safely regardless of variant input structures
        if action == 'single':
            name = (request.POST.get('students_name') or request.POST.get('name', '')).strip()
            reg_number = (request.POST.get('registration_number') or request.POST.get('reg_number', '')).strip()
            email = request.POST.get('email', '').strip()
            course_code = request.POST.get('course', '').strip() 
            
            if name and reg_number and email and course_code:
                try:
                    course = Course.objects.get(code=course_code)
                    password = generate_secure_password()
                    username = email.split('@')[0]
                    
                    user = User.objects.create_user(
                        username=username, 
                        email=email, 
                        password=password,
                        role=User.IS_STUDENT
                    )
                    user.raw_password_archive = password
                    user.save()
                    
                    StudentProfile.objects.create(
                        reg_number=reg_number,
                        user=user,
                        name=name,
                        course=course
                    )
                    messages.success(request, f"Student {name} successfully registered.")
                except Course.DoesNotExist:
                    messages.error(request, "Selected course does not exist.")
                except Exception as e:
                    messages.error(request, f"Error occurred: {str(e)}")
            
            return redirect('attendance:manage_students')

    # Fetch dependencies required for the template context
    students = StudentProfile.objects.select_related('user', 'course').all()
    courses = Course.objects.all()
    
    return render(request, 'attendance/manage_students.html', {
        'students': students,
        'active_courses_list': courses 
    })

@login_required
@transaction.atomic
def edit_student(request, pk):
    if request.user.role != User.IS_ADMIN:
        return HttpResponse("Unauthorized", status=403)
    
    student = get_object_or_404(StudentProfile, pk=pk)
    if request.method == 'POST':
        student.name = (request.POST.get('students_name') or request.POST.get('name', '')).strip()
        student.reg_number = (request.POST.get('registration_number') or request.POST.get('reg_number', '')).strip()
        student.user.email = request.POST.get('email', '').strip()
        
        course_code = request.POST.get('course', '').strip()
        try:
            student.course = Course.objects.get(code=course_code)
        except Course.DoesNotExist:
            pass
            
        student.user.save()
        student.save()
        messages.success(request, "Student records updated cleanly.")
        return redirect('attendance:manage_students')
        
    courses = Course.objects.all()
    return render(request, 'attendance/edit_student.html', {'student': student, 'active_courses_list': courses})


@login_required
@transaction.atomic
def delete_student(request, pk):
    if request.user.role != User.IS_ADMIN:
        return HttpResponse("Unauthorized", status=403)
    
    student = get_object_or_404(StudentProfile, pk=pk)
    user = student.user
    student.delete()
    user.delete()
    messages.success(request, "Student deleted from database repository.")
    return redirect('attendance:manage_students')


# =========================================================================
# 3. COURSES MANAGEMENT
# =========================================================================

@login_required
@transaction.atomic
def manage_courses(request):
    if request.user.role != User.IS_ADMIN:
        return HttpResponse("Unauthorized", status=403)

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'single' or 'course_code' in request.POST:
            code = (request.POST.get('course_code') or request.POST.get('code', '')).strip()
            name = (request.POST.get('course_name') or request.POST.get('name', '')).strip()
            if code and name:
                Course.objects.get_or_create(code=code, defaults={'name': name})
                messages.success(request, f"Course Program '{code}' integrated.")
            return redirect('attendance:manage_courses')

        elif action == 'bulk' and request.FILES.get('csv_file'):
            csv_file = request.FILES['csv_file']
            decoded_file = csv_file.read().decode('utf-8')
            reader = csv.reader(io.StringIO(decoded_file), delimiter=',')
            next(reader, None)

            for row in reader:
                if len(row) >= 2:
                    c_code, c_name = row[0].strip(), row[1].strip()
                    Course.objects.get_or_create(code=c_code, defaults={'name': c_name})
            return redirect('attendance:manage_courses')

    courses = Course.objects.all()
    return render(request, 'attendance/manage_courses.html', {'courses': courses})


@login_required
@transaction.atomic
def edit_course(request, pk):
    if request.user.role != User.IS_ADMIN:
        return HttpResponse("Unauthorized", status=403)
    
    course = get_object_or_404(Course, pk=pk)
    if request.method == 'POST':
        course.code = (request.POST.get('course_code') or request.POST.get('code', '')).strip()
        course.name = (request.POST.get('course_name') or request.POST.get('name', '')).strip()
        course.save()
        messages.success(request, "Course program updated successfully.")
        return redirect('attendance:manage_courses')
        
    return render(request, 'attendance/edit_course.html', {'course': course})


@login_required
@transaction.atomic
def delete_course(request, pk):
    if request.user.role != User.IS_ADMIN:
        return HttpResponse("Unauthorized", status=403)
    
    course = get_object_or_404(Course, pk=pk)
    course.delete()
    messages.success(request, "Course program completely wiped from scope variables.")
    return redirect('attendance:manage_courses')


# =========================================================================
# 4. COURSE UNITS MANAGEMENT
# =========================================================================

@login_required
@transaction.atomic
def manage_course_units(request):
    if request.user.role != User.IS_ADMIN:
        return HttpResponse("Unauthorized", status=403)

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'single' or 'course_unit_code' in request.POST:
            code = (request.POST.get('course_unit_code') or request.POST.get('code', '')).strip()
            name = (request.POST.get('course_unit_name') or request.POST.get('name', '')).strip()
            course_code = request.POST.get('course_code', '').strip()
            
            if code and name and course_code:
                try:
                    course = Course.objects.get(code=course_code)
                    CourseUnit.objects.get_or_create(code=code, defaults={'name': name, 'course': course})
                    messages.success(request, f"Unit module '{code}' linked directly to parent.")
                except Course.DoesNotExist:
                    messages.error(request, "Failed addition: Specified Parent Course doesn't exist.")
            return redirect('attendance:manage_course_units')

        elif action == 'bulk' and request.FILES.get('csv_file'):
            csv_file = request.FILES['csv_file']
            decoded_file = csv_file.read().decode('utf-8')
            reader = csv.reader(io.StringIO(decoded_file), delimiter=',')
            next(reader, None)

            for row in reader:
                if len(row) >= 4:
                    c_code, _, cu_code, cu_name = row[0].strip(), row[1].strip(), row[2].strip(), row[3].strip()
                    try:
                        course = Course.objects.get(code=c_code)
                        CourseUnit.objects.get_or_create(code=cu_code, defaults={'name': cu_name, 'course': course})
                    except Course.DoesNotExist:
                        continue
            return redirect('attendance:manage_course_units')

    # Optimization: prefetch parent course properties efficiently up front
    course_units = CourseUnit.objects.select_related('course').all()
    courses = Course.objects.all()
    
    # Map 'course_code' and 'course_name' explicitly as extra structural dynamic attributes 
    # to fix the template dropdown mappings without breaking underlying schema definitions
    for c in courses:
        c.course_code = c.code
        c.course_name = c.name

    return render(request, 'attendance/manage_course_units.html', {
        'course_units': course_units, 
        'courses': courses,
        'active_courses_list': courses
    })

@login_required
@transaction.atomic
def edit_course_unit(request, pk):
    if request.user.role != User.IS_ADMIN:
        return HttpResponse("Unauthorized", status=403)
        
    unit = get_object_or_404(CourseUnit, pk=pk)
    if request.method == 'POST':
        unit.code = (request.POST.get('course_unit_code') or request.POST.get('code', '')).strip()
        unit.name = (request.POST.get('course_unit_name') or request.POST.get('name', '')).strip()
        
        course_code = request.POST.get('course_code', '').strip()
        try:
            unit.course = Course.objects.get(code=course_code)
        except Course.DoesNotExist:
            pass
            
        unit.save()
        messages.success(request, "Subject Module context definitions modified successfully.")
        return redirect('attendance:manage_course_units')
        
    courses = Course.objects.all()
    return render(request, 'attendance/edit_course_unit.html', {'unit': unit, 'active_courses_list': courses})


@login_required
@transaction.atomic
def delete_course_unit(request, pk):
    if request.user.role != User.IS_ADMIN:
        return HttpResponse("Unauthorized", status=403)
        
    unit = get_object_or_404(CourseUnit, pk=pk)
    unit.delete()
    messages.success(request, "Module index row cleanly detached and purged.")
    return redirect('attendance:manage_course_units')


# =========================================================================
# 5. CORE ADMINISTRATIVE DASHBOARD & UTILITIES
# =========================================================================

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

    teacher_stats = []
    teachers = TeacherProfile.objects.all()
    for t in teachers:
        present = AttendanceRecord.objects.filter(
            session__timetable_entry__teacher=t, status='PRESENT'
        ).count()
        total = AttendanceRecord.objects.filter(session__timetable_entry__teacher=t).count()
        rate = round((present / total) * 100, 2) if total > 0 else 0
        teacher_stats.append({'name': t.name, 'rate': rate})
    
    teacher_names = [ts['name'] for ts in teacher_stats]
    teacher_rates = [ts['rate'] for ts in teacher_stats]

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
        reader = csv.reader(io.StringIO(decoded_file), delimiter=',')
        next(reader, None)  # Skip header

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
        reader = csv.reader(io.StringIO(decoded_file), delimiter=',')
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
        reader = csv.reader(io.StringIO(decoded_file), delimiter=',')
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
@transaction.atomic
def upload_timetable(request):
    if request.method == 'POST':
        use_last = request.POST.get('use_last_one') == 'true'

        if use_last:
            last_batch = TimetableBatch.objects.filter(is_revoked=False).order_by('-uploaded_at')[:1]
            if last_batch:
                TimetableBatch.objects.filter(is_active=True).update(is_active=False)
                new_batch = TimetableBatch.objects.create(week_start_date=datetime.now().date(), is_active=True)
                for entry in last_batch[0].entries.all():
                    TimetableEntry.objects.create(
                        batch=new_batch, day=entry.day, start_time=entry.start_time,
                        end_time=entry.end_time, course_unit=entry.course_unit,
                        teacher=entry.teacher, class_name=entry.class_name
                    )
                return redirect('attendance:admin_dashboard')

        csv_file = request.FILES.get('csv_file')
        if csv_file:
            TimetableBatch.objects.filter(is_active=True).update(is_active=False)
            new_batch = TimetableBatch.objects.create(week_start_date=datetime.now().date(), is_active=True)
            decoded_file = csv_file.read().decode('utf-8')
            reader = csv.reader(io.StringIO(decoded_file), delimiter=',')
            next(reader, None)

            for row in reader:
                if len(row) >= 6:
                    day, start_t, end_t, cu_code, teacher_email, class_name = row
                    try:
                        cu = CourseUnit.objects.get(code=cu_code.strip())
                        teacher = TeacherProfile.objects.get(user__email=teacher_email.strip())
                        TimetableEntry.objects.create(
                            batch=new_batch, day=day.strip(),
                            start_time=datetime.strptime(start_t.strip(), '%H:%M').time(),
                            end_time=datetime.strptime(end_t.strip(), '%H:%M').time(),
                            course_unit=cu, teacher=teacher, class_name=class_name.strip()
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


# =========================================================================
# 6. CREDENTIAL EXPORTS ENGINE (EXCEL OUTPUT FORMAT)
# =========================================================================

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill

@login_required
def export_credentials(request, role_type):
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

    for col in ws.columns:
        max_length = max(len(str(cell.value or '')) for cell in col)
        column = col[0].column_letter
        ws.column_dimensions[column].width = max_length + 2

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{role_type}_credentials.xlsx"'
    wb.save(response)
    return response