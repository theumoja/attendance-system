from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('root/admin/', admin.site.urls),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', include('core.urls')),
]

# LINK CUSTOM ERROR HANDLERS TO CORE VIEWS
handler404 = 'core.views.custom_page_not_found'
handler403 = 'core.views.custom_permission_denied'
handler500 = 'core.views.custom_server_error'
handler400 = 'core.views.custom_bad_request'