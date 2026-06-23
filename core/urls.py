from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Auth
    path('login/', views.custom_login, name='login'),

    # Home & signup
    path('', views.home, name='home'),
    path('signup/', views.signup_view, name='signup'),
    path('pending-approval/', views.PendingApprovalView.as_view(), name='pending_approval'),

    # Admin
    path('admin/dashboard/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('admin/courses/', views.AdminCourseListView.as_view(), name='admin_courses'),
    path('admin/courses/create/', views.AdminCourseCreateView.as_view(), name='admin_course_create'),
    path('admin/courses/<int:pk>/update/', views.AdminCourseUpdateView.as_view(), name='admin_course_update'),
    path('admin/courses/<int:pk>/delete/', views.AdminCourseDeleteView.as_view(), name='admin_course_delete'),
    path('admin/enrollments/', views.AdminManageEnrollmentsView.as_view(), name='admin_enrollments'),
    path('admin/reports/', views.AdminReportsView.as_view(), name='admin_reports'),
    path('admin/approve-teachers/', views.AdminTeacherApprovalsView.as_view(), name='admin_teacher_approvals'),
    path('superuser/approve-admins/', views.superuser_admin_approvals, name='superuser_admin_approvals'),

    # Teacher
    path('teacher/dashboard/', views.TeacherDashboardView.as_view(), name='teacher_dashboard'),
    path('teacher/courses/<int:course_id>/units/', views.TeacherCourseUnitsView.as_view(), name='teacher_course_units'),
    path('teacher/units/<int:unit_id>/mark-attendance/', views.TeacherMarkAttendanceView.as_view(), name='teacher_mark_attendance'),
    path('teacher/units/<int:unit_id>/attendance/', views.TeacherAttendanceView.as_view(), name='teacher_attendance'),
    path('teacher/approve-students/', views.TeacherStudentApprovalsView.as_view(), name='teacher_student_approvals'),

    # Student
    path('student/dashboard/', views.StudentDashboardView.as_view(), name='student_dashboard'),
    path('student/courses/<int:course_id>/units/', views.StudentCourseUnitsView.as_view(), name='student_course_units'),
    path('student/units/<int:unit_id>/attendance/', views.StudentAttendanceView.as_view(), name='student_attendance'),
]