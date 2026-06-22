# attendance_system/urls.py
from django.urls import path, include
from django.contrib.auth import views as auth_views
from core.admin_site import custom_admin_site   # import the custom admin

urlpatterns = [
    path('admin/', custom_admin_site.urls),     # use custom admin
    path('login/', auth_views.LoginView.as_view(
        template_name='core/login.html',
        redirect_authenticated_user=True,
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', include('core.urls')),
]