from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import TemplateView, ListView, DetailView, View, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from .models import Course, CourseUnit, Enrollment, TeacherAssignment, AttendanceRecord
from .mixins import GroupRequiredMixin
from django.contrib.auth.models import User

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import TemplateView, ListView, View, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User, Group
from django.utils import timezone
from .models import Course, CourseUnit, Enrollment, TeacherAssignment, AttendanceRecord, Profile
from .mixins import GroupRequiredMixin
from .forms import SignupForm


# ---------- Signup and Approval Flow ----------

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
            if profile.role in ['Student', 'Teacher']:
                profile.courses.set(form.cleaned_data['courses'])
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
            for course in profile.courses.all():
                TeacherAssignment.objects.get_or_create(teacher=profile.user, course=course)
            messages.success(request, f'Teacher {profile.user.username} approved.')
        elif action == 'reject':
            # Simply delete the user or mark rejected (we'll delete for simplicity)
            user = profile.user
            profile.delete()
            user.delete()
            messages.success(request, f'Teacher {profile.user.username} rejected and removed.')
        return redirect('core:admin_teacher_approvals')

# ---------- Teacher Approval for Students ----------
class TeacherStudentApprovalsView(GroupRequiredMixin, TemplateView):
    group_name = 'Teacher'
    template_name = 'core/teacher/student_approvals.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get courses taught by this teacher
        teacher_courses = TeacherAssignment.objects.filter(
            teacher=self.request.user
        ).values_list('course_id', flat=True)
        # Pending student profiles who applied to these courses
        pending_profiles = Profile.objects.filter(
            role='Student',
            is_approved=False,
            courses__id__in=teacher_courses
        ).distinct().select_related('user').prefetch_related('courses')
        context['profiles'] = pending_profiles
        return context

    def post(self, request, *args, **kwargs):
        profile_id = request.POST.get('profile_id')
        action = request.POST.get('action')
        profile = get_object_or_404(Profile, pk=profile_id, role='Student', is_approved=False)

        if action == 'approve':
            profile.is_approved = True
            profile.save()
            student_group, _ = Group.objects.get_or_create(name='Student')
            profile.user.groups.add(student_group)
            # Create Enrollments for courses that the teacher teaches and the student applied for
            teacher_courses = TeacherAssignment.objects.filter(
                teacher=request.user
            ).values_list('course_id', flat=True)
            for course in profile.courses.filter(id__in=teacher_courses):
                Enrollment.objects.get_or_create(student=profile.user, course=course)
            messages.success(request, f'Student {profile.user.username} approved.')
        elif action == 'reject':
            user = profile.user
            profile.delete()
            user.delete()
            messages.success(request, f'Student {profile.user.username} rejected and removed.')
        return redirect('core:teacher_student_approvals')

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

# ---------- Home Redirect (Modified) ----------
@login_required
def home(request):
    user = request.user
    profile = user.profile
    if not profile.is_approved:
        return redirect('core:pending_approval')
    # Proceed as before
    if user.groups.filter(name='Student').exists():
        return redirect('core:student_dashboard')
    elif user.groups.filter(name='Teacher').exists():
        return redirect('core:teacher_dashboard')
    elif user.groups.filter(name='Admin').exists():
        return redirect('core:admin_dashboard')
    else:
        return redirect('/admin/')

# ---------- Keep all existing views from earlier (Student, Teacher, Admin dashboards etc.) ----------
# ... (copy all previous class-based views exactly as before)

# Role-based home redirect
@login_required
def home(request):
    user = request.user
    if user.groups.filter(name='Student').exists():
        return redirect('core:student_dashboard')
    elif user.groups.filter(name='Teacher').exists():
        return redirect('core:teacher_dashboard')
    elif user.groups.filter(name='Admin').exists():
        return redirect('core:admin_dashboard')
    else:
        # fallback (should not happen)
        return redirect('/admin/')

# ---------- Student Views ----------
class StudentDashboardView(GroupRequiredMixin, TemplateView):
    group_name = 'Student'
    template_name = 'core/student/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['enrollments'] = Enrollment.objects.filter(student=self.request.user).select_related('course')
        return context

class StudentCourseUnitsView(GroupRequiredMixin, ListView):
    group_name = 'Student'
    template_name = 'core/student/course_units.html'
    context_object_name = 'units'

    def get_queryset(self):
        self.course = get_object_or_404(Course, pk=self.kwargs['course_id'])
        return CourseUnit.objects.filter(course=self.course)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.course
        return context

class StudentAttendanceView(GroupRequiredMixin, ListView):
    group_name = 'Student'
    template_name = 'core/student/attendance.html'
    context_object_name = 'records'

    def get_queryset(self):
        self.unit = get_object_or_404(CourseUnit, pk=self.kwargs['unit_id'])
        return AttendanceRecord.objects.filter(
            student=self.request.user,
            course_unit=self.unit
        ).order_by('-date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unit'] = self.unit
        return context

# ---------- Teacher Views ----------
class TeacherDashboardView(GroupRequiredMixin, TemplateView):
    group_name = 'Teacher'
    template_name = 'core/teacher/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['assignments'] = TeacherAssignment.objects.filter(
            teacher=self.request.user
        ).select_related('course')
        return context

class TeacherCourseUnitsView(GroupRequiredMixin, ListView):
    group_name = 'Teacher'
    template_name = 'core/teacher/course_units.html'
    context_object_name = 'units'

    def get_queryset(self):
        course = get_object_or_404(Course, pk=self.kwargs['course_id'])
        # Ensure teacher is assigned to this course
        get_object_or_404(TeacherAssignment, teacher=self.request.user, course=course)
        return CourseUnit.objects.filter(course=course)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = get_object_or_404(Course, pk=self.kwargs['course_id'])
        return context

class TeacherMarkAttendanceView(GroupRequiredMixin, View):
    group_name = 'Teacher'
    template_name = 'core/teacher/mark_attendance.html'

    def get(self, request, unit_id):
        unit = get_object_or_404(CourseUnit, pk=unit_id)
        course = unit.course
        get_object_or_404(TeacherAssignment, teacher=request.user, course=course)
        # students enrolled in the course
        enrolled_students = User.objects.filter(
            enrollment__course=course,
            groups__name='Student'
        ).distinct()
        # check existing attendance for today
        today = timezone.now().date()
        existing = AttendanceRecord.objects.filter(
            course_unit=unit,
            date=today
        ).values_list('student_id', flat=True)
        context = {
            'unit': unit,
            'course': course,
            'students': enrolled_students,
            'existing': list(existing),
        }
        return render(request, self.template_name, context)

    def post(self, request, unit_id):
        unit = get_object_or_404(CourseUnit, pk=unit_id)
        course = unit.course
        get_object_or_404(TeacherAssignment, teacher=request.user, course=course)
        today = timezone.now().date()
        lat = request.POST.get('lat')
        lon = request.POST.get('lon')
        # loop over all enrolled students
        enrolled_students = User.objects.filter(
            enrollment__course=course,
            groups__name='Student'
        ).distinct()
        for student in enrolled_students:
            present = request.POST.get(f'present_{student.id}') == 'on'
            AttendanceRecord.objects.update_or_create(
                student=student,
                course_unit=unit,
                date=today,
                defaults={
                    'is_present': present,
                    'teacher_gps_lat': lat,
                    'teacher_gps_lon': lon,
                    'marked_by': request.user,
                }
            )
        messages.success(request, 'Attendance recorded successfully.')
        return redirect('core:teacher_course_units', course_id=course.id)

class TeacherAttendanceView(GroupRequiredMixin, ListView):
    group_name = 'Teacher'
    template_name = 'core/teacher/attendance.html'
    context_object_name = 'records'

    def get_queryset(self):
        self.unit = get_object_or_404(CourseUnit, pk=self.kwargs['unit_id'])
        course = self.unit.course
        get_object_or_404(TeacherAssignment, teacher=self.request.user, course=course)
        return AttendanceRecord.objects.filter(course_unit=self.unit).order_by('-date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unit'] = self.unit
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

# Manage enrollments (teachers & students per course)
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

        # calculate per-student attendance percentage
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