from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from attendance import views_admin, views_users, views_analytics, views

app_name = 'attendance'

urlpatterns = [
    # Baseline Root Landing Page Routing
    path('', views_users.home, name='home'),
    # Auth routing infrastructure
    path('login/', views.custom_login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Execution Environment Hubs
    path('dashboard/', views_admin.admin_dashboard, name='admin_dashboard'),
    path('teacher/dashboard/', views_users.teacher_dashboard, name='teacher_dashboard'),
    path('student/dashboard/', views_users.student_dashboard, name='student_dashboard'),

    # Data pipeline ingest arrays
    path('admin-ui/upload/courses/', views_admin.bulk_upload_courses, name='bulk_upload_courses'),
    path('admin-ui/upload/teachers/', views_admin.bulk_upload_teachers, name='bulk_upload_teachers'),
    path('admin-ui/upload/students/', views_admin.bulk_upload_students, name='bulk_upload_students'),
    path('admin-ui/upload/timetable/', views_admin.upload_timetable, name='upload_timetable'),

    # Outbound structural export arrays
    path('admin-ui/export/credentials/<str:role_type>/', views_admin.export_credentials, name='export_credentials'),
    path('admin-ui/download-template/<str:template_type>/', views_admin.download_template, name='download_template'),

    # Interactive interface transaction routes
    path('teacher/attendance/mark/<int:entry_id>/', views_users.mark_attendance, name='mark_attendance'),

    # Telemetry streaming engine data feeds
    path('analytics/global/json/', views_analytics.global_analytics_data, name='global_analytics_data'),

    # Student report download
    path('student/report/download/', views_users.download_student_report, name='download_student_report'),
]