# core/admin_site.py
from django.contrib.admin import AdminSite
from django.urls import reverse_lazy
from django.shortcuts import redirect  # Added missing import


class CustomAdminSite(AdminSite):
    site_header = "Attendance System Admin"
    site_title = "Admin Portal"
    index_title = "Dashboard"
    login_template = 'core/login.html'  # use YOUR custom login template

    def login(self, request, extra_context=None):
        # Redirect to your custom login view when not authenticated
        if not request.user.is_authenticated:
            return redirect('%s?next=%s' % (reverse_lazy('login'), request.path))
        return super().login(request, extra_context)

# Instantiate it
custom_admin_site = CustomAdminSite(name='custom_admin')