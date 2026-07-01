import json
import csv
from io import BytesIO
from itertools import groupby
from operator import attrgetter

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.urls import reverse

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill

from attendance.models import (
    User, TimetableEntry, StudentProfile, AttendanceSession,
    AttendanceRecord, CourseUnit
)

@login_required
def home(request):
    """
    Redirects the user to their appropriate dashboard based on their role.
    """
    if request.user.role == User.IS_ADMIN:
        return redirect('attendance:admin_dashboard')
    elif request.user.role == User.IS_TEACHER:
        return redirect('attendance:teacher_dashboard')
    else:
        return redirect('attendance:student_dashboard')


@login_required
def mark_attendance(request, entry_id):
    # Authorization check
    if not hasattr(request.user, 'teacher_profile') or request.user.teacher_profile is None:
        return HttpResponse("Unauthorized", status=403)

    entry = get_object_or_404(TimetableEntry, id=entry_id, teacher=request.user.teacher_profile)
    
    # MODIFIED: Filters roster strictly to students belonging to this precise stream
    students = StudentProfile.objects.filter(stream=entry.stream)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            lat = data.get('latitude')
            lng = data.get('longitude')
            records = data.get('records', {})

            session = AttendanceSession.objects.create(
                timetable_entry=entry,
                teacher_latitude=lat,
                teacher_longitude=lng
            )

            for student_reg, status in records.items():
                student = StudentProfile.objects.get(reg_number=student_reg)
                AttendanceRecord.objects.create(session=session, student=student, status=status)

            # Redirect to the home view – it will send teachers to the teacher dashboard
            return JsonResponse({
                'status': 'success',
                'redirect_url': reverse('attendance:home')
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return render(request, 'attendance/mark_attendance.html', {'entry': entry, 'students': students})
    

@login_required
def student_dashboard(request):
    """
    Displays personal attendance summary, historical records, and analytics charts for a student.
    """
    if request.user.role != User.IS_STUDENT:
        return HttpResponse("Unauthorized", status=403)
        
    student = request.user.student_profile
    records = AttendanceRecord.objects.filter(student=student).select_related('session__timetable_entry__course_unit')
    
    # Track overall stats alongside course unit stats
    unit_attendance = {}
    total_present = 0
    total_absent = 0
    
    for rec in records:
        cu_name = rec.session.timetable_entry.course_unit.name
        if cu_name not in unit_attendance:
            unit_attendance[cu_name] = {'present': 0, 'absent': 0}
            
        if rec.status == 'PRESENT':
            unit_attendance[cu_name]['present'] += 1
            total_present += 1
        else:
            unit_attendance[cu_name]['absent'] += 1
            total_absent += 1
    
    unit_names = list(unit_attendance.keys())
    present_counts = [unit_attendance[u]['present'] for u in unit_names]
    absent_counts = [unit_attendance[u]['absent'] for u in unit_names]

    context = {
        'records': records,
        'total_present': total_present,
        'total_absent': total_absent,
        'unit_names': json.dumps(unit_names),
        'present_counts': json.dumps(present_counts),
        'absent_counts': json.dumps(absent_counts),
        'student': student,
    }
    return render(request, 'attendance/student_dashboard.html', context)


@login_required
def teacher_dashboard(request):
    """
    Displays scheduled timetable slots, registered student scopes, 
    and recent submission feeds broken down by date logs.
    """
    if request.user.role != User.IS_TEACHER:
        return HttpResponse("Unauthorized", status=403)
        
    teacher = request.user.teacher_profile
    timetable = TimetableEntry.objects.filter(
        batch__is_active=True, teacher=teacher
    ).select_related('course_unit', 'batch')
    
    course_units = CourseUnit.objects.filter(timetableentry__teacher=teacher).distinct()
    students = StudentProfile.objects.filter(course__units__in=course_units).distinct()
    
    # Stats per unit
    unit_stats = []
    for cu in course_units:
        present = AttendanceRecord.objects.filter(
            session__timetable_entry__course_unit=cu,
            session__timetable_entry__teacher=teacher,
            status='PRESENT'
        ).count()
        total = AttendanceRecord.objects.filter(
            session__timetable_entry__course_unit=cu,
            session__timetable_entry__teacher=teacher
        ).count()
        rate = round((present / total) * 100, 2) if total > 0 else 0
        unit_stats.append({'name': cu.name, 'rate': rate})
    
    # Recent records – group by date
    recent_records = AttendanceRecord.objects.filter(
        session__timetable_entry__teacher=teacher
    ).select_related(
        'session__timetable_entry__course_unit',
        'student'
    ).order_by('-session__date_marked')[:20]

    # Group the records by date
    grouped_by_date = {}
    for rec in recent_records:
        date_key = rec.session.date_marked
        grouped_by_date.setdefault(date_key, []).append(rec)
    
    # Convert to a list of tuples sorted by date descending
    grouped_records = sorted(grouped_by_date.items(), key=lambda x: x[0], reverse=True)

    unit_names = [u['name'] for u in unit_stats]
    unit_rates = [u['rate'] for u in unit_stats]

    week_start = None
    active_batch = timetable.first().batch if timetable else None
    if active_batch:
        week_start = active_batch.week_start_date

    context = {
        'timetable': timetable,
        'students': students,
        'course_units': course_units,
        'unit_names': json.dumps(unit_names),
        'unit_rates': json.dumps(unit_rates),
        'week_start': week_start,
        'grouped_records': grouped_records,
    }
    return render(request, 'attendance/teacher_dashboard.html', context)


@login_required
def download_student_report(request):
    if request.user.role != User.IS_STUDENT:
        return HttpResponse("Unauthorized", status=403)

    student = request.user.student_profile
    # Added select_related for the stream relation to keep query lookup efficient
    records = AttendanceRecord.objects.filter(student=student).select_related(
        'session__timetable_entry__course_unit',
        'session__timetable_entry__teacher',
        'session__timetable_entry__stream'
    )

    # Create Excel workbook using openpyxl
    wb = Workbook()
    ws = wb.active
    ws.title = "Attendance Report"

    # Headers updated to represent the Stream architecture
    headers = ['Course Unit', 'Date', 'Status', 'Stream', 'Teacher']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')
        cell.fill = PatternFill(start_color='d3d3d3', end_color='d3d3d3', fill_type='solid')

    # Data rows
    for row_num, rec in enumerate(records, start=2):
        session = rec.session
        entry = session.timetable_entry
        ws.cell(row=row_num, column=1, value=entry.course_unit.name)
        ws.cell(row=row_num, column=2, value=session.date_marked.strftime('%Y-%m-%d'))
        ws.cell(row=row_num, column=3, value=rec.status)
        ws.cell(row=row_num, column=4, value=entry.stream.name if entry.stream else "") # Changed from entry.class_name
        ws.cell(row=row_num, column=5, value=entry.teacher.name)

    # Auto-adjust column widths dynamically
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
    response['Content-Disposition'] = f'attachment; filename=\"attendance_report_{student.reg_number}.xlsx\"'
    wb.save(response)
    return response

# ---------- Custom Error Handlers ----------

def custom_page_not_found(request, exception):
    return render(request, 'errors/404.html', status=404)

def custom_permission_denied(request, exception=None):
    return render(request, 'errors/403.html', status=403)

def custom_server_error(request):
    return render(request, 'errors/500.html', status=500)

def custom_bad_request(request, exception=None):
    return render(request, 'errors/400.html', status=400)