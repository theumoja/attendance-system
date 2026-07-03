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
from attendance.models import *


def generate_secure_password():
    return secrets.token_urlsafe(8)

@login_required
@transaction.atomic
def manage_streams(request):
    if request.user.role != User.IS_ADMIN:
        return HttpResponse("Unauthorized", status=403)

    if request.method == 'POST':
        name = request.POST.get('stream_name', '').strip()
        course_code = request.POST.get('course_code', '').strip()
        
        if name and course_code:
            try:
                course = Course.objects.get(code=course_code)
                Stream.objects.create(name=name, course=course)
                messages.success(request, f"Stream '{name}' successfully registered.")
            except Course.DoesNotExist:
                messages.error(request, "The specified parent course layout does not exist.")
            except Exception as e:
                messages.error(request, f"Error building structural layout: {str(e)}")
        else:
            messages.error(request, "All required input layout items must be filled.")
        return redirect('attendance:manage_streams')

    streams = Stream.objects.select_related('course').all()
    courses = Course.objects.all()
    return render(request, 'attendance/manage_streams.html', {
        'streams': streams,
        'courses': courses
    })

@login_required
@transaction.atomic
def edit_stream(request, stream_id):
    if request.user.role != User.IS_ADMIN:
        return HttpResponse("Unauthorized", status=403)

    stream_obj = get_object_or_404(Stream, id=stream_id)
    if request.method == 'POST':
        name = request.POST.get('stream_name', '').strip()
        course_code = request.POST.get('course_code', '').strip()
        
        if name and course_code:
            try:
                course = Course.objects.get(code=course_code)
                stream_obj.name = name
                stream_obj.course = course
                stream_obj.save()
                messages.success(request, "Structural stream modifications compiled securely.")
                return redirect('attendance:manage_streams')
            except Course.DoesNotExist:
                messages.error(request, "Target parent course layout context does not exist.")
        else:
            messages.error(request, "Fields cannot be blank.")

    courses = Course.objects.all()
    return render(request, 'attendance/edit_stream.html', {
        'stream': stream_obj,
        'courses': courses
    })

@login_required
@transaction.atomic
def delete_stream(request, stream_id):
    if request.user.role != User.IS_ADMIN:
        return HttpResponse("Unauthorized", status=403)

    stream_obj = get_object_or_404(Stream, id=stream_id)
    name = stream_obj.name
    stream_obj.delete()
    messages.success(request, f"Stream framework structure '{name}' detached successfully.")
    return redirect('attendance:manage_streams')

@login_required
@transaction.atomic
def bulk_upload_streams(request):
    if request.user.role != User.IS_ADMIN:
        return HttpResponse("Unauthorized", status=403)

    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        if not csv_file.name.endswith('.csv'):
            messages.error(request, "Data error: Expected standard comma-delimited flat CSV file structure.")
            return redirect('attendance:bulk_upload_streams')

        try:
            stream_data = csv_file.read().decode('utf-8')
            io_string = io.StringIO(stream_data)
            reader = csv.reader(io_string)
            next(reader, None)

            success_count = 0
            for row in reader:
                if not row or len(row) < 2:
                    continue
                stream_name = row[0].strip()
                course_code = row[1].strip()

                if stream_name and course_code:
                    course = Course.objects.filter(code=course_code).first()
                    if course:
                        Stream.objects.get_or_create(name=stream_name, course=course)
                        success_count += 1

            messages.success(request, f"Ingested {success_count} unique structural academic stream mappings.")
            return redirect('attendance:manage_streams')
        except Exception as e:
            messages.error(request, f"Parser exception detected: {str(e)}")

    return render(request, 'attendance/bulk_upload_streams.html')

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
        
        if action == 'single':
            name = (request.POST.get('students_name') or request.POST.get('name', '')).strip()
            reg_number = (request.POST.get('registration_number') or request.POST.get('reg_number', '')).strip()
            email = request.POST.get('email', '').strip()
            course_code = request.POST.get('course', '').strip() 
            stream_id = request.POST.get('stream', '').strip()
            
            if name and reg_number and email and course_code:
                try:
                    course = Course.objects.get(code=course_code)
                    stream = Stream.objects.get(id=stream_id) if stream_id else None
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
                        course=course,
                        stream=stream
                    )
                    messages.success(request, f"Student {name} successfully registered.")
                except Course.DoesNotExist:
                    messages.error(request, "Selected course does not exist.")
                except Stream.DoesNotExist:
                    messages.error(request, "Selected stream does not exist.")
                except Exception as e:
                    messages.error(request, f"Error occurred: {str(e)}")
            
            return redirect('attendance:manage_students')

    students = StudentProfile.objects.select_related('user', 'course', 'stream').all()
    courses = Course.objects.all()
    streams = Stream.objects.all()
    
    return render(request, 'attendance/manage_students.html', {
        'students': students,
        'active_courses_list': courses,
        'streams': streams
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
        stream_id = request.POST.get('stream', '').strip()
        try:
            student.course = Course.objects.get(code=course_code)
        except Course.DoesNotExist:
            pass

        try:
            student.stream = Stream.objects.get(id=stream_id) if stream_id else None
        except Stream.DoesNotExist:
            pass
            
        student.user.save()
        student.save()
        messages.success(request, "Student records updated cleanly.")
        return redirect('attendance:manage_students')
        
    courses = Course.objects.all()
    streams = Stream.objects.filter(course=student.course)
    return render(request, 'attendance/edit_student.html', {
        'student': student, 
        'active_courses_list': courses,
        'streams': streams
    })


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
# NEW. DEPARTMENTS MANAGEMENT
# =========================================================================

@login_required
@transaction.atomic
def manage_departments(request):
    if request.user.role != User.IS_ADMIN:
        return HttpResponse("Unauthorized", status=403)

    if request.method == 'POST':
        name = request.POST.get('department_name', '').strip()
        if name:
            Department.objects.get_or_create(name=name)
            messages.success(request, f"Department '{name}' successfully integrated.")
        else:
            messages.error(request, "Department name value cannot be blank.")
        return redirect('attendance:manage_departments')

    departments = Department.objects.all()
    return render(request, 'attendance/manage_departments.html', {'departments': departments})

@login_required
def add_department(request):
    """
    Handles the structural ingestion and creation of a new academic department.
    """
    if request.user.role != User.IS_ADMIN:
        return HttpResponse("Unauthorized", status=403)

    if request.method == 'POST':
        dept_name = request.POST.get('department_name', '').strip()
        
        if not dept_name:
            messages.error(request, "Department name cannot be empty.")
            return redirect('attendance:manage_departments')
            
        # Check for duplication framework arrays
        if Department.objects.filter(name__iexact=dept_name).exists():
            messages.error(request, f"The department '{dept_name}' already exists.")
            return redirect('attendance:manage_departments')
            
        # Create structural track entry
        Department.objects.create(name=dept_name)
        messages.success(request, f"Department '{dept_name}' successfully configured.")
        
    return redirect('attendance:manage_departments')

    
@login_required
@transaction.atomic
def edit_department(request, pk):
    if request.user.role != User.IS_ADMIN:
        return HttpResponse("Unauthorized", status=403)
    
    department = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        name = request.POST.get('department_name', '').strip()
        if name:
            department.name = name
            department.save()
            messages.success(request, "Department structural identifier modified successfully.")
            return redirect('attendance:manage_departments')
        else:
            messages.error(request, "Department fields cannot be blank.")
            
    return render(request, 'attendance/edit_department.html', {'department': department})


@login_required
@transaction.atomic
def delete_department(request, pk):
    if request.user.role != User.IS_ADMIN:
        return HttpResponse("Unauthorized", status=403)
    
    department = get_object_or_404(Department, pk=pk)
    name = department.name
    department.delete()
    messages.success(request, f"Department '{name}' cleanly detached from application context.")
    return redirect('attendance:manage_departments')


# =========================================================================
# 3. COURSES MANAGEMENT (UPDATED FOR DEPARTMENTS)
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
            department_id = request.POST.get('department', '').strip()
            
            if code and name:
                dept = Department.objects.filter(id=department_id).first() if department_id else None
                course, created = Course.objects.get_or_create(code=code, defaults={'name': name, 'department': dept})
                if not created:
                    course.name = name
                    course.department = dept
                    course.save()
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
                    if c_code:  # Safety guard for bulk uploads
                        Course.objects.get_or_create(code=c_code, defaults={'name': c_name})
            return redirect('attendance:manage_courses')

    # FIX: Exclude any corrupted empty or null text rows from the stream
    courses = Course.objects.select_related('department').exclude(code="").exclude(code__isnull=True)
    departments = Department.objects.all()
    
    return render(request, 'attendance/manage_courses.html', {
        'courses': courses,
        'departments': departments
    })

@login_required
@transaction.atomic
def edit_course(request, pk):
    if request.user.role != User.IS_ADMIN:
        return HttpResponse("Unauthorized", status=403)
    
    course = get_object_or_404(Course, pk=pk)
    if request.method == 'POST':
        course.code = (request.POST.get('course_code') or request.POST.get('code', '')).strip()
        course.name = (request.POST.get('course_name') or request.POST.get('name', '')).strip()
        department_id = request.POST.get('department', '').strip()
        
        if department_id:
            course.department = Department.objects.filter(id=department_id).first()
        else:
            course.department = None
            
        course.save()
        messages.success(request, "Course program updated successfully.")
        return redirect('attendance:manage_courses')
        
    departments = Department.objects.all()
    return render(request, 'attendance/edit_course.html', {
        'course': course,
        'departments': departments
    })


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

    course_units = CourseUnit.objects.select_related('course').all()
    courses = Course.objects.all()
    
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

    stream_counts = Stream.objects.select_related('course').annotate(
        student_count=Count('students')
    ).order_by('name')

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
        'stream_counts': stream_counts,
    }
    return render(request, 'attendance/admin_dashboard.html', context)


@login_required
@transaction.atomic
def bulk_upload_courses(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        decoded_file = csv_file.read().decode('utf-8')
        reader = csv.reader(io.StringIO(decoded_file), delimiter=',')
        next(reader, None)

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
            if len(row) >= 5:
                name, reg_num, email, course_code, stream_name = row[0].strip(), row[1].strip(), row[2].strip(), row[3].strip(), row[4].strip()
                try:
                    course = Course.objects.get(code=course_code)
                    
                    from attendance.models import Stream
                    stream_obj, _ = Stream.objects.get_or_create(name=stream_name, course=course)
                    
                    password = generate_secure_password()
                    user, created = User.objects.get_or_create(email=email, defaults={
                        'username': reg_num.replace('/', '_'),
                        'role': User.IS_STUDENT,
                        'raw_password_archive': password
                    })
                    if created:
                        user.set_password(password)
                        user.save()
                        StudentProfile.objects.create(user=user, reg_number=reg_num, name=name, course=course, stream=stream_obj)
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
                        teacher=entry.teacher, stream=entry.stream
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
                    day, start_t, end_t, cu_code, teacher_email, stream_name = row
                    try:
                        cu = CourseUnit.objects.get(code=cu_code.strip())
                        teacher = TeacherProfile.objects.get(user__email=teacher_email.strip())
                        
                        from attendance.models import Stream
                        stream_obj, _ = Stream.objects.get_or_create(
                            name=stream_name.strip(),
                            course=cu.course
                        )
                        
                        TimetableEntry.objects.create(
                            batch=new_batch, day=day.strip(),
                            start_time=datetime.strptime(start_t.strip(), '%H:%M').time(),
                            end_time=datetime.strptime(end_t.strip(), '%H:%M').time(),
                            course_unit=cu, teacher=teacher, stream=stream_obj
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
        content = "students_name,registration_number,email,course,stream_name\nAlice Smith,2024/001,alice@example.com,CIT,Year 1 CIT A"
    elif template_type == 'timetable':
        content = "day,start_time,end_time,course_unit_code,teacher_email,stream_name\nMON,08:30,10:00,CIT101,james.muwonge@utc.ac.ug,Year 1 CIT A"
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


# =========================================================================
# NEW. ADMINISTRATIVE REPORTS VIEW
# =========================================================================


@login_required
def admin_report_page(request):
    # Enforce Admin-only access
    if request.user.role != User.IS_ADMIN:
        return HttpResponse("Unauthorized", status=403)
        
    departments = Department.objects.all()
    
    # Extract structural query constraint parameter directly from backend request arrays
    selected_dept_id = request.GET.get('filter_dept')
    
    # Start with base layout mapping matching all active structural course matrices
    courses = Course.objects.select_related('department').all()
    
    # Execute structural filtering directly inside database processing layers if constraint exists
    if selected_dept_id:
        courses = courses.filter(department_id=selected_dept_id)
        try:
            selected_dept_id = int(selected_dept_id)  # Standardize type matching for UI template rules
        except ValueError:
            selected_dept_id = None

    return render(request, 'attendance/admin_report.html', {
        'departments': departments,
        'courses': courses,
        'selected_dept_id': selected_dept_id
    })

'''
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
import json
from attendance.models import User, Stream, AttendanceRecord, AttendanceSession, StudentProfile

@login_required
def analytics_dashboard(request):

    # Enforce strict Admin-only access rule matrix
    if request.user.role != User.IS_ADMIN:
        return HttpResponse("Unauthorized", status=403)

    # Extract optional filter parameters from template request scopes
    selected_stream_id = request.GET.get('stream')
    
    # Base query sets targeting core transactional datasets
    records = AttendanceRecord.objects.all()
    sessions = AttendanceSession.objects.select_related(
        'timetable_entry__teacher__user', 
        'timetable_entry__stream'
    ).order_by('-date_marked')
    
    # Dynamic application of scoping filters if requested by the end-user
    if selected_stream_id and selected_stream_id != 'all':
        records = records.filter(student__stream_id=selected_stream_id)
        sessions = sessions.filter(timetable_entry__stream_id=selected_stream_id)

    # 1. Compute Live Summary Statistics Metrics Matrix
    total_records = records.count()
    present_count = records.filter(status='PRESENT').count()
    absent_count = records.filter(status='ABSENT').count()

    stats = {
        'total_records': total_records,
        'present_rate': round((present_count / total_records) * 100, 1) if total_records > 0 else 0,
        'absent_rate': round((absent_count / total_records) * 100, 1) if total_records > 0 else 0,
        'late_rate': 0  # Maintained at 0 since model STATUS_CHOICES only specifies PRESENT/ABSENT
    }

    # 2. Compile Lecturer Location Audit Log Dataset Dynamically
    audit_logs = []
    # Fetching the top 20 latest session instances to prevent UI buffer layout breaks
    for session in sessions[:20]:
        t_entry = session.timetable_entry
        has_coords = session.teacher_latitude is not None and session.teacher_longitude is not None
        
        location_str = f"{session.teacher_latitude}, {session.teacher_longitude}" if has_coords else "Not captured"
        
        audit_logs.append({
            "date": session.date_marked.strftime("%Y-%m-%d") if session.date_marked else "—",
            "class": t_entry.stream.name if t_entry.stream else "—",
            "lecturer": t_entry.teacher.user.email if t_entry.teacher and t_entry.teacher.user else "—",
            "location": location_str,
            "ip": "—",  # Placeholder asset as IP capture hooks are not defined inside current models schema
            "verified": has_coords  # Flag verified true strictly if geolocation values exist
        })

    # 3. Pull Top Students Metrics Arrays via Database Annotations
    students = StudentProfile.objects.select_related('stream').annotate(
        total_rec=Count('attendancerecord'),
        present_rec=Count('attendancerecord', filter=Q(attendancerecord__status='PRESENT'))
    ).filter(total_rec__gt=0)
    
    top_students_raw = []
    for s in students:
        rate = (s.present_rec / s.total_rec) * 100
        top_students_raw.append({
            "name": s.name,
            "reg": s.reg_number,
            "class": s.stream.name if s.stream else "—",
            "rate_num": rate,
            "rate": f"{round(rate, 1)}%"
        })
    
    # Sort and slice dataset to grab top performing arrays
    top_students = sorted(top_students_raw, key=lambda x: x['rate_num'], reverse=True)[:5]

    # 4. Generate Aggregated Payload Engines for ChartJS
    # Chart A: Global Present vs Absent distribution count vectors
    chart_dist_data = [present_count, absent_count]
    
    # Chart B: Generate stream breakdown labels and cross-cutting attendance percentage matrices
    streams_data = Stream.objects.annotate(
        total=Count('students__attendancerecord'),
        present=Count('students__attendancerecord', filter=Q(students__attendancerecord__status='PRESENT'))
    ).filter(total__gt=0)
    
    stream_labels = [stream.name for stream in streams_data]
    stream_rates = [round((stream.present / stream.total) * 100, 1) for stream in streams_data]

    # Context compilation pass payload arrays safely out into frontend DOM nodes
    context = {
        'stats': stats,
        'audit_logs': audit_logs,
        'top_students': top_students,
        'streams': Stream.objects.all(),
        'selected_stream': selected_stream_id,
        'chart_dist_data': json.dumps(chart_dist_data),
        'stream_labels': json.dumps(stream_labels),
        'stream_rates': json.dumps(stream_rates),
    }
    return render(request, 'attendance/analytics_dashboard.html', context)
    if request.user.role != User.IS_ADMIN:
        return HttpResponse("Unauthorized", status=403)

    # 1. Summary Statistics Metrics
    stats = {
        'total_records': 10,
        'present_rate': 90,
        'absent_rate': 10,
        'late_rate': 0
    }

    # 2. Lecturer Location Audit Log Dataset
    audit_logs = [
        {"date": "2026-06-26 @ 15:21", "class": "NDEE Weekend", "lecturer": "laban.omenyo.ai@gmail.com", "location": "0.3375, 32.5943 (±193642m)", "ip": "41.210.154.15", "verified": True},
        {"date": "2026-06-25 @ 21:45", "class": "NDME A", "lecturer": "technologiestescal@gmail.com", "location": "-0.6195, 30.6697 (±65m)", "ip": "41.210.154.139", "verified": True},
        {"date": "2026-05-18 @ 16:20", "class": "NDEE Weekend", "lecturer": "technologiestescal@gmail.com", "location": "-0.5470, 30.2457 (±130m)", "ip": "154.72.206.194", "verified": True},
        {"date": "2026-05-10 @ 09:13", "class": "NDEE Weekend", "lecturer": "technologiestescal@gmail.com", "location": "-0.5469, 30.2457 (±68m)", "ip": "41.210.146.63", "verified": True},
        {"date": "2026-05-10 @ 22:06", "class": "NDME A", "lecturer": "technologiestescal@gmail.com", "location": "Not captured", "ip": "41.210.146.63", "verified": True},
        {"date": "2026-05-10 @ 21:54", "class": "NDME A", "lecturer": "technologiestescal@gmail.com", "location": "-0.5502, 30.2441 (±30m)", "ip": "41.210.146.63", "verified": False},
        {"date": "2026-05-10 @ 12:36", "class": "NDA A", "lecturer": "technologiestescal@gmail.com", "location": "-0.5469, 30.2457 (±61m)", "ip": "154.72.206.194", "verified": True},
        {"date": "2026-05-10 @ 12:35", "class": "NDA A", "lecturer": "technologiestescal@gmail.com", "location": "Not captured", "ip": "154.72.206.194", "verified": False},
        {"date": "2026-05-08 @ 22:54", "class": "NDEE Weekend", "lecturer": "—", "location": "Not captured", "ip": "—", "verified": False},
        {"date": "2026-05-09 @ 22:33", "class": "NDA A", "lecturer": "—", "location": "Not captured", "ip": "—", "verified": False},
        {"date": "2026-05-09 @ 10:57", "class": "NDEE Weekend", "lecturer": "—", "location": "Not captured", "ip": "—", "verified": False},
        {"date": "2026-05-09 @ 10:39", "class": "NDME A", "lecturer": "—", "location": "Not captured", "ip": "—", "verified": False},
    ]

    # 3. Top Students Placeholder Data Structure
    top_students = [
        {"name": "Mukasa John", "reg": "2025/NDEE/021", "class": "NDEE Weekend", "rate": "98%"},
        {"name": "Ainomugisha Dianah", "reg": "2025/NDME/104", "class": "NDME A", "rate": "96%"},
        {"name": "Mwesigye Brian", "reg": "2025/NDA/008", "class": "NDA A", "rate": "95%"},
    ]

    context = {
        'stats': stats,
        'audit_logs': audit_logs,
        'top_students': top_students,
    }
    return render(request, 'attendance/analytics_dashboard.html', context)



'''
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from datetime import datetime, timedelta
import json
import csv
from attendance.models import User, Department, Course, Stream, AttendanceRecord, AttendanceSession, StudentProfile

@login_required
def analytics_dashboard(request):
    # Enforce strict Admin-only access rule matrix
    if request.user.role != User.IS_ADMIN:
        return HttpResponse("Unauthorized", status=403)

    # 1. CAPTURE DETAILED REPORT FILTERS
    filter_dept = request.GET.get('filter_dept')
    filter_course = request.GET.get('filter_course')
    filter_stream = request.GET.get('filter_stream')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    quick_range = request.GET.get('quick_range')

    # Base entity dropdown datasets supporting cascading display lists
    all_departments = Department.objects.all()
    selectable_courses = Course.objects.all()
    selectable_streams = Stream.objects.all()

    if filter_dept:
        selectable_courses = selectable_courses.filter(department_id=filter_dept)
    if filter_course:
        selectable_streams = selectable_streams.filter(course__code=filter_course)

    # 2. RESOLVE TIME DATA WINDOW CONSTRAINTS
    today = datetime.now().date()
    start_date = None
    end_date = None

    if quick_range == 'today':
        start_date = today
        end_date = today
    elif quick_range == 'week':
        start_date = today - timedelta(days=7)
        end_date = today
    elif quick_range == 'month':
        start_date = today - timedelta(days=30)
        end_date = today
    else:
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

    # Build cross-cutting performance filter arrays
    record_date_filter = Q()
    if start_date:
        record_date_filter &= Q(attendancerecord__session__date_marked__gte=start_date)
    if end_date:
        record_date_filter &= Q(attendancerecord__session__date_marked__lte=end_date)

    # 3. COMPILE COMPLETE DETAILED STUDENT POPULATION ROSTER
    report_students_queryset = StudentProfile.objects.select_related('stream', 'course__department').all()
    
    if filter_stream:
        report_students_queryset = report_students_queryset.filter(stream_id=filter_stream)
    elif filter_course:
        report_students_queryset = report_students_queryset.filter(course__code=filter_course)
    elif filter_dept:
        report_students_queryset = report_students_queryset.filter(course__department_id=filter_dept)

    # Calculate absolute percentages over selected date parameters
    annotated_students = report_students_queryset.annotate(
        total_filtered_records=Count('attendancerecord', filter=record_date_filter),
        present_filtered_records=Count('attendancerecord', filter=record_date_filter & Q(attendancerecord__status='PRESENT'))
    ).order_by('name')

    detailed_student_reports = []
    for s in annotated_students:
        tot = s.total_filtered_records
        pres = s.present_filtered_records
        percentage_val = round((pres / tot) * 100, 1) if tot > 0 else 0.0
        
        detailed_student_reports.append({
            "name": s.name,
            "reg_number": s.reg_number,
            "stream_name": s.stream.name if s.stream else "—",
            "total_logs": tot,
            "present_logs": pres,
            "attendance_percentage": f"{percentage_val}%",
            "percentage_num": percentage_val
        })

    # 4. INTERCEPT SPECIFIC DETAILED EXPORT REQUESTS
    if request.GET.get('export') == 'detailed_student_csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="detailed_student_report_{today}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Student Name', 'Registration Number', 'Assigned Stream', 'Total Sessions Checked', 'Sessions Attended', 'Attendance Rate'])
        for item in detailed_student_reports:
            writer.writerow([item['name'], item['reg_number'], item['stream_name'], item['total_logs'], item['present_logs'], item['attendance_percentage']])
        return response

    # 5. PRESERVE ORIGINAL ANALYTICS COMPONENT ARRAYS
    selected_stream_id = request.GET.get('stream')
    records = AttendanceRecord.objects.all()
    sessions = AttendanceSession.objects.select_related('timetable_entry__teacher__user', 'timetable_entry__stream').order_by('-date_marked')
    
    if selected_stream_id and selected_stream_id != 'all':
        records = records.filter(student__stream_id=selected_stream_id)
        sessions = sessions.filter(timetable_entry__stream_id=selected_stream_id)

    # Process original global metrics
    total_records = records.count()
    present_count = records.filter(status='PRESENT').count()
    absent_count = records.filter(status='ABSENT').count()

    stats = {
        'total_records': total_records,
        'present_rate': round((present_count / total_records) * 100, 1) if total_records > 0 else 0,
        'absent_rate': round((absent_count / total_records) * 100, 1) if total_records > 0 else 0,
    }

    # Location Log Parsing
    audit_logs = []
    for session in sessions[:20]:
        t_entry = session.timetable_entry
        has_coords = session.teacher_latitude is not None and session.teacher_longitude is not None
        location_str = f"{session.teacher_latitude}, {session.teacher_longitude}" if has_coords else "Not captured"
        audit_logs.append({
            "date": session.date_marked.strftime("%Y-%m-%d") if session.date_marked else "—",
            "class": t_entry.stream.name if t_entry.stream else "—",
            "lecturer": t_entry.teacher.user.email if t_entry.teacher and t_entry.teacher.user else "—",
            "location": location_str,
            "ip": "—",  
            "verified": has_coords  
        })

    # Standard Top-20 Matrix Ingestion 
    students = StudentProfile.objects.select_related('stream').annotate(
        total_rec=Count('attendancerecord'),
        present_rec=Count('attendancerecord', filter=Q(attendancerecord__status='PRESENT')),
        absent_rec=Count('attendancerecord', filter=Q(attendancerecord__status='ABSENT'))
    ).filter(total_rec__gt=0)
    
    students_raw = []
    for s in students:
        p_rate = (s.present_rec / s.total_rec) * 100
        a_rate = (s.absent_rec / s.total_rec) * 100
        students_raw.append({
            "name": s.name,
            "reg": s.reg_number,
            "class": s.stream.name if s.stream else "—",
            "p_rate_num": p_rate,
            "a_rate_num": a_rate,
            "p_rate": f"{round(p_rate, 1)}%",
            "a_rate": f"{round(a_rate, 1)}%"
        })
    
    top_present_students = sorted(students_raw, key=lambda x: x['p_rate_num'], reverse=True)[:20]
    top_absent_students = sorted(students_raw, key=lambda x: x['a_rate_num'], reverse=True)[:20]

    # Lecturer Compliance Ingestion
    TimetableEntry = AttendanceSession._meta.get_field('timetable_entry').related_model
    total_system_sessions = sessions.count()
    teacher_counts = sessions.values('timetable_entry__teacher_id').annotate(count=Count('id'))
    counts_map = {item['timetable_entry__teacher_id']: item['count'] for item in teacher_counts if item['timetable_entry__teacher_id']}
    timetable_entries = TimetableEntry.objects.select_related('teacher__user').all()
    
    if selected_stream_id and selected_stream_id != 'all':
        timetable_entries = timetable_entries.filter(stream_id=selected_stream_id)

    teachers_raw = []
    seen_teachers = set()
    for entry in timetable_entries:
        if entry.teacher and entry.teacher.id not in seen_teachers:
            seen_teachers.add(entry.teacher.id)
            email = entry.teacher.user.email if entry.teacher.user else "—"
            submitted = counts_map.get(entry.teacher.id, 0)
            rate = round((submitted / total_system_sessions) * 100, 1) if total_system_sessions > 0 else 0
            teachers_raw.append({'email': email, 'submitted': submitted, 'rate': f"{rate}%"})

    top_submitted_teachers = sorted(teachers_raw, key=lambda x: x['submitted'], reverse=True)[:20]
    top_unsubmitted_teachers = sorted(teachers_raw, key=lambda x: x['submitted'], reverse=False)[:20]

    # Chart Generation Data Processing
    chart_dist_data = [present_count, absent_count]
    streams_data = Stream.objects.annotate(
        total=Count('students__attendancerecord'),
        present=Count('students__attendancerecord', filter=Q(students__attendancerecord__status='PRESENT'))
    ).filter(total__gt=0)
    
    stream_labels = [stream.name for stream in streams_data]
    stream_rates = [round((stream.present / stream.total) * 100, 1) for stream in streams_data]

    context = {
        'stats': stats,
        'audit_logs': audit_logs,
        'top_present_students': top_present_students,
        'top_absent_students': top_absent_students,
        'top_submitted_teachers': top_submitted_teachers,
        'top_unsubmitted_teachers': top_unsubmitted_teachers,
        'streams': Stream.objects.all(),
        'selected_stream': selected_stream_id,
        'chart_dist_data': json.dumps(chart_dist_data),
        'stream_labels': json.dumps(stream_labels),
        'stream_rates': json.dumps(stream_rates),
        
        # New Detailed reporting fields injected safely into context context
        'departments': all_departments,
        'courses': selectable_courses,
        'selectable_streams': selectable_streams,
        'detailed_student_reports': detailed_student_reports,
        'filter_dept': filter_dept,
        'filter_course': filter_course,
        'filter_stream': filter_stream,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'quick_range': quick_range,
    }
    return render(request, 'attendance/analytics_dashboard.html', context)
    # Enforce strict Admin-only access rule matrix
    if request.user.role != User.IS_ADMIN:
        return HttpResponse("Unauthorized", status=403)

    # Extract optional filter parameters from template request scopes
    selected_stream_id = request.GET.get('stream')
    
    # 1. INITIALIZE VARIABLES FIRST (Fixes UnboundLocalError)
    # Base query sets targeting core transactional datasets
    records = AttendanceRecord.objects.all()
    sessions = AttendanceSession.objects.select_related(
        'timetable_entry__teacher__user', 
        'timetable_entry__stream'
    ).order_by('-date_marked')
    
    # 2. APPLY SCOPING FILTERS dynamically if requested
    if selected_stream_id and selected_stream_id != 'all':
        records = records.filter(student__stream_id=selected_stream_id)
        sessions = sessions.filter(timetable_entry__stream_id=selected_stream_id)

    # 3. INTERCEPT CSV EXPORT REQUEST
    # Now that 'records' exists and is filtered, we can safely export it!
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="attendance_report.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Student Name', 'Reg Number', 'Class/Stream', 'Status', 'Date'])
        
        # NOTE: If your relation to AttendanceSession is named something else 
        # (e.g. 'attendance_session'), change 'session' below to match your models.py
        for record in records.select_related('student__stream', 'session'):
            date_val = record.session.date_marked.strftime('%Y-%m-%d') if hasattr(record, 'session') and record.session.date_marked else 'N/A'
            stream_name = record.student.stream.name if record.student.stream else 'N/A'
            
            writer.writerow([
                record.student.name, 
                record.student.reg_number,
                stream_name,
                record.status, 
                date_val
            ])
        return response

    # 4. Compute Live Summary Statistics Metrics Matrix
    total_records = records.count()
    present_count = records.filter(status='PRESENT').count()
    absent_count = records.filter(status='ABSENT').count()

    stats = {
        'total_records': total_records,
        'present_rate': round((present_count / total_records) * 100, 1) if total_records > 0 else 0,
        'absent_rate': round((absent_count / total_records) * 100, 1) if total_records > 0 else 0,
    }

    # 5. Compile Lecturer Location Audit Log Dataset Dynamically
    audit_logs = []
    for session in sessions[:20]:
        t_entry = session.timetable_entry
        has_coords = session.teacher_latitude is not None and session.teacher_longitude is not None
        location_str = f"{session.teacher_latitude}, {session.teacher_longitude}" if has_coords else "Not captured"
        
        audit_logs.append({
            "date": session.date_marked.strftime("%Y-%m-%d") if session.date_marked else "—",
            "class": t_entry.stream.name if t_entry.stream else "—",
            "lecturer": t_entry.teacher.user.email if t_entry.teacher and t_entry.teacher.user else "—",
            "location": location_str,
            "ip": "—",  
            "verified": has_coords  
        })

    # 6. Pull Top Present & Absent Students Metrics Arrays via Database Annotations (Top 20)
    students = StudentProfile.objects.select_related('stream').annotate(
        total_rec=Count('attendancerecord'),
        present_rec=Count('attendancerecord', filter=Q(attendancerecord__status='PRESENT')),
        absent_rec=Count('attendancerecord', filter=Q(attendancerecord__status='ABSENT'))
    ).filter(total_rec__gt=0)
    
    students_raw = []
    for s in students:
        p_rate = (s.present_rec / s.total_rec) * 100
        a_rate = (s.absent_rec / s.total_rec) * 100
        students_raw.append({
            "name": s.name,
            "reg": s.reg_number,
            "class": s.stream.name if s.stream else "—",
            "p_rate_num": p_rate,
            "a_rate_num": a_rate,
            "p_rate": f"{round(p_rate, 1)}%",
            "a_rate": f"{round(a_rate, 1)}%"
        })
    
    top_present_students = sorted(students_raw, key=lambda x: x['p_rate_num'], reverse=True)[:20]
    top_absent_students = sorted(students_raw, key=lambda x: x['a_rate_num'], reverse=True)[:20]

    # 7. Generate Teacher Attendance Submission Compliance Metrics Report
    TimetableEntry = AttendanceSession._meta.get_field('timetable_entry').related_model
    total_system_sessions = sessions.count()

    teacher_counts = sessions.values('timetable_entry__teacher_id').annotate(count=Count('id'))
    counts_map = {item['timetable_entry__teacher_id']: item['count'] for item in teacher_counts if item['timetable_entry__teacher_id']}

    timetable_entries = TimetableEntry.objects.select_related('teacher__user').all()
    if selected_stream_id and selected_stream_id != 'all':
        timetable_entries = timetable_entries.filter(stream_id=selected_stream_id)

    teachers_raw = []
    seen_teachers = set()

    for entry in timetable_entries:
        if entry.teacher and entry.teacher.id not in seen_teachers:
            seen_teachers.add(entry.teacher.id)
            email = entry.teacher.user.email if entry.teacher.user else "—"
            submitted = counts_map.get(entry.teacher.id, 0)
            
            rate = round((submitted / total_system_sessions) * 100, 1) if total_system_sessions > 0 else 0
            
            teachers_raw.append({
                'email': email,
                'submitted': submitted,
                'rate': f"{rate}%"
            })

    top_submitted_teachers = sorted(teachers_raw, key=lambda x: x['submitted'], reverse=True)[:20]
    top_unsubmitted_teachers = sorted(teachers_raw, key=lambda x: x['submitted'], reverse=False)[:20]

    # 8. Generate Aggregated Payload Engines for ChartJS
    chart_dist_data = [present_count, absent_count]
    
    streams_data = Stream.objects.annotate(
        total=Count('students__attendancerecord'),
        present=Count('students__attendancerecord', filter=Q(students__attendancerecord__status='PRESENT'))
    ).filter(total__gt=0)
    
    stream_labels = [stream.name for stream in streams_data]
    stream_rates = [round((stream.present / stream.total) * 100, 1) for stream in streams_data]

    context = {
        'stats': stats,
        'audit_logs': audit_logs,
        'top_present_students': top_present_students,
        'top_absent_students': top_absent_students,
        'top_submitted_teachers': top_submitted_teachers,
        'top_unsubmitted_teachers': top_unsubmitted_teachers,
        'streams': Stream.objects.all(),
        'selected_stream': selected_stream_id,
        'chart_dist_data': json.dumps(chart_dist_data),
        'stream_labels': json.dumps(stream_labels),
        'stream_rates': json.dumps(stream_rates),
    }
    return render(request, 'attendance/analytics_dashboard.html', context)