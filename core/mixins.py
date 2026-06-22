from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied

class GroupRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    group_name = None

    def test_func(self):
        return self.request.user.groups.filter(name=self.group_name).exists()

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied