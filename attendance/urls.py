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
    
    # Core Directory Management Views
    path('user-admin/manage-teachers/', views_admin.manage_teachers, name='manage_teachers'),
    path('user-admin/manage-students/', views_admin.manage_students, name='manage_students'),
    path('user-admin/manage-courses/', views_admin.manage_courses, name='manage_courses'),
    path('user-admin/manage-course-units/', views_admin.manage_course_units, name='manage_course_units'),

    # =========================================================================
    # CRITICAL RECORD EDIT / DELETE ROUTING ENGINE
    # =========================================================================
    
    # Teachers CRUD Extensions (Standard Auto-Increment Integer Keys)
    path('user-admin/manage-teachers/edit/<int:pk>/', views_admin.edit_teacher, name='edit_teacher'),
    path('user-admin/manage-teachers/delete/<int:pk>/', views_admin.delete_teacher, name='delete_teacher'),

    # Students CRUD Extensions (FIXED: Uses path to accommodate slashes in Reg Numbers)
    path('user-admin/manage-students/edit/<path:pk>/', views_admin.edit_student, name='edit_student'),
    path('user-admin/manage-students/delete/<path:pk>/', views_admin.delete_student, name='delete_student'),

    # Courses CRUD Extensions (String Alphanumeric Primary Keys)
    path('user-admin/manage-courses/edit/<str:pk>/', views_admin.edit_course, name='edit_course'),
    path('user-admin/manage-courses/delete/<str:pk>/', views_admin.delete_course, name='delete_course'),

    # Course Units CRUD Extensions (String Alphanumeric Primary Keys)
    path('user-admin/manage-course-units/edit/<str:pk>/', views_admin.edit_course_unit, name='edit_course_unit'),
    path('user-admin/manage-course-units/delete/<str:pk>/', views_admin.delete_course_unit, name='delete_course_unit'),
    path('change-password/', views.change_password_view, name='change_password'),

    path('management/streams/', views_admin.manage_streams, name='manage_streams'),
    path('management/streams/edit/<int:stream_id>/', views_admin.edit_stream, name='edit_stream'),
    path('management/streams/delete/<int:stream_id>/', views_admin.delete_stream, name='delete_stream'),
    path('management/streams/bulk-upload/', views_admin.bulk_upload_streams, name='bulk_upload_streams'),


    # Department Management Routes
    path('departments/', views_admin.manage_departments, name='manage_departments'),
    path('departments/edit/<int:pk>/', views_admin.edit_department, name='edit_department'),
    path('departments/delete/<int:pk>/', views_admin.delete_department, name='delete_department'),
    path('departments/reports/', views_admin.admin_report_page, name='admin_report_page'),
    path('student/download-card/', views_users.download_attendance_card, name='download_attendance_card'),


    path('departments/add/', views_admin.add_department, name='add_department'),
    path('analytics/', views_admin.analytics_dashboard, name='analytics_dashboard'),
    path('admin-ui/upload/timetable/pdf/', views_admin.export_timetable_pdf, name='export_timetable_pdf'),
]