from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy

class GroupRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    group_name = None
    login_url = reverse_lazy('login')          # <-- add this

    def test_func(self):
        return self.request.user.groups.filter(name=self.group_name).exists()

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied