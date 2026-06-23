from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import TemplateView, ListView, View, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User, Group
from django.utils import timezone
from .models import (
    Course, CourseUnit, TeacherAssignment,
    StudentUnitEnrollment, AttendanceRecord, Profile
)
from .mixins import GroupRequiredMixin
from .forms import SignupForm
from datetime import datetime # Add this import at the top

# ---------- Custom Login ----------
def custom_login(request):
    if request.user.is_authenticated:
        return redirect('core:home')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', reverse('core:home'))
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'core/login.html')



# core/views.py (Replace these specific functions/views within your file)

@login_required
def home(request):
    user = request.user
    profile = user.profile

    # Handle Role Authentication Separately
    if profile.role == 'Student':
        # Students bypass global approval; checking for at least one active course enrollment approval
        if not StudentUnitEnrollment.objects.filter(student=user, is_approved=True).exists():
            return redirect('core:pending_approval')
    else:
        if not profile.is_approved:
            return redirect('core:pending_approval')

    if user.is_superuser:
        return redirect('/admin/dashboard')

    if user.groups.filter(name='Student').exists():
        return redirect('core:student_dashboard')
    elif user.groups.filter(name='Teacher').exists():
        return redirect('core:teacher_dashboard')
    elif user.groups.filter(name='Admin').exists():
        return redirect('core:admin_dashboard')

    messages.error(request, 'Your account has no assigned role. Please contact an administrator.')
    return redirect('core:login')


# core/views.py

# --- UPDATE TEACHER APPROVALS VIEW SYSTEM ---
class TeacherStudentApprovalsView(GroupRequiredMixin, TemplateView):
    group_name = 'Teacher'
    template_name = 'core/teacher/teacher_student_approvals.html' 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher_courses = TeacherAssignment.objects.filter(teacher=self.request.user).values_list('course_id', flat=True)
        units = CourseUnit.objects.filter(course_id__in=teacher_courses)
        
        # Pull records that are brand new OR have been resubmitted
        context['pending_enrollments'] = StudentUnitEnrollment.objects.filter(
            course_unit__in=units,
            status__in=['PENDING', 'REAPPLIED']
        ).select_related('student', 'course_unit__course').order_by('course_unit')
        
        context['approved_enrollments'] = StudentUnitEnrollment.objects.filter(
            course_unit__in=units,
            status='APPROVED'
        ).select_related('student', 'course_unit__course').order_by('course_unit')
        
        return context

    def post(self, request, *args, **kwargs):
        enrollment_id = request.POST.get('enrollment_id')
        action = request.POST.get('action')
        enrollment = get_object_or_404(StudentUnitEnrollment, pk=enrollment_id)
        
        if not TeacherAssignment.objects.filter(teacher=request.user, course=enrollment.course_unit.course).exists():
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied

        if action == 'approve':
            enrollment.is_approved = True
            enrollment.status = 'APPROVED'
            enrollment.save()
            
            student_group, _ = Group.objects.get_or_create(name='Student')
            enrollment.student.groups.add(student_group)
            
            student_profile = enrollment.student.profile
            student_profile.is_approved = True
            student_profile.save()
            
            messages.success(request, f'{enrollment.student.username} approved for {enrollment.course_unit.code}.')
        elif action in ['reject', 'revoke']:
            # Soft change state instead of deleting
            enrollment.is_approved = False
            enrollment.status = 'REVOKED'
            enrollment.save()
            messages.success(request, f'Revoked enrollment for {enrollment.student.username} from unit {enrollment.course_unit.code}.')
            
        return redirect('core:teacher_student_approvals')


# --- UPDATE TEACHER DASHBOARD VIEW POST METHOD ---
class TeacherDashboardView(GroupRequiredMixin, TemplateView):
    group_name = 'Teacher'
    template_name = 'core/teacher/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        assignments = TeacherAssignment.objects.filter(teacher=self.request.user).select_related('course')
        context['assignments'] = assignments
        
        teacher_courses = assignments.values_list('course_id', flat=True)
        units = CourseUnit.objects.filter(course_id__in=teacher_courses)
        context['pending_enrollments'] = StudentUnitEnrollment.objects.filter(
            course_unit__in=units,
            status__in=['PENDING', 'REAPPLIED']
        ).select_related('student', 'course_unit__course').order_by('course_unit')
        
        return context

    def post(self, request, *args, **kwargs):
        enrollment_id = request.POST.get('enrollment_id')
        action = request.POST.get('action')
        enrollment = get_object_or_404(StudentUnitEnrollment, pk=enrollment_id)
        
        if not TeacherAssignment.objects.filter(teacher=request.user, course=enrollment.course_unit.course).exists():
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied

        if action == 'approve':
            enrollment.is_approved = True
            enrollment.status = 'APPROVED'
            enrollment.save()
            
            student_group, _ = Group.objects.get_or_create(name='Student')
            enrollment.student.groups.add(student_group)
            
            student_profile = enrollment.student.profile
            student_profile.is_approved = True
            student_profile.save()
            messages.success(request, f'{enrollment.student.username} approved.')
        elif action == 'reject':
            enrollment.is_approved = False
            enrollment.status = 'REVOKED'
            enrollment.save()
            messages.success(request, 'Enrollment status updated to Revoked.')
            
        return redirect('core:teacher_dashboard')





# --- NEW REAPPLY CONTROLLER ---
@login_required
@user_passes_test(lambda u: u.groups.filter(name='Student').exists())
def student_reapply_unit(request, enrollment_id):
    if request.method == 'POST':
        enrollment = get_object_or_404(StudentUnitEnrollment, pk=enrollment_id, student=request.user, status='REVOKED')
        enrollment.status = 'REAPPLIED'
        enrollment.is_approved = False
        enrollment.save()
        messages.success(request, f"Successfully sent re-application for {enrollment.course_unit.code}.")
    return redirect('core:student_dashboard')

def signup_view(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
            )
            profile = user.profile
            profile.role = form.cleaned_data['role']
            profile.save()

            if profile.role == 'Teacher':
                profile.applied_courses.set(form.cleaned_data['courses'])
                profile.applied_units.clear()
            elif profile.role == 'Student':
                # Get the units from the form
                selected_units = form.cleaned_data['units']
                profile.applied_units.set(selected_units)
                profile.applied_courses.clear()
                
                # --- FIX: Create the pending entries so they show up for the teacher ---
                for unit in selected_units:
                    StudentUnitEnrollment.objects.get_or_create(
                        student=user,
                        course_unit=unit,
                        defaults={'is_approved': False}
                    )
            else:  # Admin
                profile.applied_courses.clear()
                profile.applied_units.clear()

            messages.success(request, 'Account created! Please wait for approval.')
            return redirect('core:pending_approval')
    else:
        form = SignupForm()
    return render(request, 'core/signup.html', {'form': form})


class PendingApprovalView(TemplateView):
    template_name = 'core/pending_approval.html'


# ---------- Admin Approval for Teachers ----------
class AdminTeacherApprovalsView(GroupRequiredMixin, ListView):
    group_name = 'Admin'
    template_name = 'core/admin/teacher_approvals.html'
    context_object_name = 'profiles'

    def get_queryset(self):
        return Profile.objects.filter(role='Teacher', is_approved=False).select_related('user')

    def post(self, request, *args, **kwargs):
        profile_id = request.POST.get('profile_id')
        action = request.POST.get('action')
        profile = get_object_or_404(Profile, pk=profile_id, role='Teacher', is_approved=False)

        if action == 'approve':
            profile.is_approved = True
            profile.save()
            teacher_group, _ = Group.objects.get_or_create(name='Teacher')
            profile.user.groups.add(teacher_group)
            # Create TeacherAssignment for each applied course
            for course in profile.applied_courses.all():
                TeacherAssignment.objects.get_or_create(teacher=profile.user, course=course)
            messages.success(request, f'Teacher {profile.user.username} approved.')
        elif action == 'reject':
            user = profile.user
            profile.delete()
            user.delete()
            messages.success(request, f'Teacher {profile.user.username} rejected and removed.')
        return redirect('core:admin_teacher_approvals')




# ---------- Superuser Approval for Admins ----------
@user_passes_test(lambda u: u.is_superuser)
def superuser_admin_approvals(request):
    profiles = Profile.objects.filter(role='Admin', is_approved=False).select_related('user')
    if request.method == 'POST':
        profile_id = request.POST.get('profile_id')
        action = request.POST.get('action')
        profile = get_object_or_404(Profile, pk=profile_id, role='Admin', is_approved=False)
        if action == 'approve':
            profile.is_approved = True
            profile.save()
            admin_group, _ = Group.objects.get_or_create(name='Admin')
            profile.user.groups.add(admin_group)
            messages.success(request, f'Admin {profile.user.username} approved.')
        elif action == 'reject':
            user = profile.user
            profile.delete()
            user.delete()
            messages.success(request, f'Admin {profile.user.username} rejected and removed.')
        return redirect('core:superuser_admin_approvals')
    return render(request, 'core/admin/admin_approvals.html', {'profiles': profiles})



# --- UPDATE STUDENT DASHBOARD VIEW ---
class StudentDashboardView(GroupRequiredMixin, TemplateView):
    group_name = 'Student'
    template_name = 'core/student/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Active and accessible units
        context['enrollments'] = StudentUnitEnrollment.objects.filter(
            student=self.request.user,
            status='APPROVED'
        ).select_related('course_unit__course')
        
        # Track historical records, application delays, and blocks
        context['other_enrollments'] = StudentUnitEnrollment.objects.filter(
            student=self.request.user
        ).exclude(status='APPROVED').select_related('course_unit__course')
        return context

# Optional: view to list units of a course (if still needed)
class StudentCourseUnitsView(GroupRequiredMixin, ListView):
    group_name = 'Student'
    template_name = 'core/student/course_units.html'
    context_object_name = 'units'

    def get_queryset(self):
        course = get_object_or_404(Course, pk=self.kwargs['course_id'])
        # Only units the student is approved for
        return CourseUnit.objects.filter(
            course=course,
            enrollments__student=self.request.user,
            enrollments__is_approved=True
        ).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = get_object_or_404(Course, pk=self.kwargs['course_id'])
        return context


class StudentAttendanceView(GroupRequiredMixin, ListView):
    group_name = 'Student'
    template_name = 'core/student/attendance.html'
    context_object_name = 'records'

    def get_queryset(self):
        unit = get_object_or_404(CourseUnit, pk=self.kwargs['unit_id'])
        # Ensure student is approved for this unit
        get_object_or_404(StudentUnitEnrollment, student=self.request.user, course_unit=unit, is_approved=True)
        return AttendanceRecord.objects.filter(
            student=self.request.user,
            course_unit=unit
        ).order_by('-date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unit'] = get_object_or_404(CourseUnit, pk=self.kwargs['unit_id'])
        return context





class TeacherMarkAttendanceView(GroupRequiredMixin, View):
    group_name = 'Teacher'
    template_name = 'core/teacher/mark_attendance.html'

    def get(self, request, unit_id):
        unit = get_object_or_404(CourseUnit, pk=unit_id)
        course = unit.course
        get_object_or_404(TeacherAssignment, teacher=request.user, course=course)
        
        # Check if the teacher selected a specific date, otherwise default to today
        date_str = request.GET.get('date')
        if date_str:
            try:
                selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                selected_date = timezone.now().date()
        else:
            selected_date = timezone.now().date()

        # Only approved students for this unit
        approved = StudentUnitEnrollment.objects.filter(
            course_unit=unit,
            is_approved=True
        ).select_related('student')
        students = [enr.student for enr in approved]
        
        # Fetch status checkmarks for the chosen date
        existing = AttendanceRecord.objects.filter(
            course_unit=unit,
            date=selected_date
        ).values_list('student_id', flat=True)
        
        context = {
            'unit': unit,
            'course': course,
            'students': students,
            'existing': list(existing),
            'selected_date': selected_date.strftime('%Y-%m-%d'),
        }
        return render(request, self.template_name, context)

    def post(self, request, unit_id):
        unit = get_object_or_404(CourseUnit, pk=unit_id)
        course = unit.course
        get_object_or_404(TeacherAssignment, teacher=request.user, course=course)
        
        # Read the date submitted by the form
        date_str = request.POST.get('attendance_date')
        if date_str:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            target_date = timezone.now().date()
            
        lat = request.POST.get('lat')
        lon = request.POST.get('lon')
        
        approved_students = StudentUnitEnrollment.objects.filter(
            course_unit=unit,
            is_approved=True
        ).values_list('student_id', flat=True)

        for student_id in approved_students:
            student = User.objects.get(pk=student_id)
            present = request.POST.get(f'present_{student.id}') == 'on'
            
            # This safely updates or inserts data for that EXACT target date
            AttendanceRecord.objects.update_or_create(
                student=student,
                course_unit=unit,
                date=target_date,
                defaults={
                    'is_present': present,
                    'teacher_gps_lat': lat,
                    'teacher_gps_lon': lon,
                    'marked_by': request.user,
                }
            )
        messages.success(request, f'Attendance for {target_date} recorded successfully.')
        return redirect('core:teacher_course_units', course_id=course.id)
class TeacherCourseUnitsView(GroupRequiredMixin, ListView):
    group_name = 'Teacher'
    template_name = 'core/teacher/course_units.html'
    context_object_name = 'units'

    def get_queryset(self):
        course = get_object_or_404(Course, pk=self.kwargs['course_id'])
        get_object_or_404(TeacherAssignment, teacher=self.request.user, course=course)
        return CourseUnit.objects.filter(course=course)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = get_object_or_404(Course, pk=self.kwargs['course_id'])
        return context




class TeacherAttendanceView(GroupRequiredMixin, ListView):
    group_name = 'Teacher'
    template_name = 'core/teacher/attendance.html'
    context_object_name = 'records'

    def get_queryset(self):
        unit = get_object_or_404(CourseUnit, pk=self.kwargs['unit_id'])
        course = unit.course
        get_object_or_404(TeacherAssignment, teacher=self.request.user, course=course)
        
        # FIX: select_related('student') optimizes performance, 
        # and ordering by '-date' then 'student__username' builds perfect day-by-day sub-lists
        return AttendanceRecord.objects.filter(course_unit=unit).select_related('student').order_by('-date', 'student__username')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unit'] = get_object_or_404(CourseUnit, pk=self.kwargs['unit_id'])
        return context


# ---------- Admin Views ----------
class AdminDashboardView(GroupRequiredMixin, TemplateView):
    group_name = 'Admin'
    template_name = 'core/admin/dashboard.html'


# Course CRUD
class AdminCourseListView(GroupRequiredMixin, ListView):
    group_name = 'Admin'
    model = Course
    template_name = 'core/admin/course_list.html'
    context_object_name = 'courses'


class AdminCourseCreateView(GroupRequiredMixin, CreateView):
    group_name = 'Admin'
    model = Course
    fields = ['name', 'code', 'description']
    template_name = 'core/admin/course_form.html'
    success_url = reverse_lazy('core:admin_courses')


class AdminCourseUpdateView(GroupRequiredMixin, UpdateView):
    group_name = 'Admin'
    model = Course
    fields = ['name', 'code', 'description']
    template_name = 'core/admin/course_form.html'
    success_url = reverse_lazy('core:admin_courses')


class AdminCourseDeleteView(GroupRequiredMixin, DeleteView):
    group_name = 'Admin'
    model = Course
    template_name = 'core/admin/course_confirm_delete.html'
    success_url = reverse_lazy('core:admin_courses')


# Manage enrollments (placeholder)
class AdminManageEnrollmentsView(GroupRequiredMixin, TemplateView):
    group_name = 'Admin'
    template_name = 'core/admin/manage_enrollments.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['courses'] = Course.objects.all()
        return context


class AdminReportsView(GroupRequiredMixin, TemplateView):
    group_name = 'Admin'
    template_name = 'core/admin/reports.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course_id = self.request.GET.get('course')
        unit_id = self.request.GET.get('unit')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        records = AttendanceRecord.objects.all()

        if course_id:
            records = records.filter(course_unit__course_id=course_id)
        if unit_id:
            records = records.filter(course_unit_id=unit_id)
        if date_from:
            records = records.filter(date__gte=date_from)
        if date_to:
            records = records.filter(date__lte=date_to)

        from django.db.models import Count, Q
        students = User.objects.filter(groups__name='Student')
        report = []
        for student in students:
            total = records.filter(student=student).count()
            present = records.filter(student=student, is_present=True).count()
            percent = (present / total * 100) if total > 0 else 0
            report.append({
                'student': student.username,
                'total': total,
                'present': present,
                'percent': round(percent, 1)
            })

        context['report'] = report
        context['courses'] = Course.objects.all()
        context['units'] = CourseUnit.objects.all()
        context['filters'] = {
            'course': course_id,
            'unit': unit_id,
            'date_from': date_from,
            'date_to': date_to,
        }
        return context