# core/management/commands/fix_superuser_group.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group

class Command(BaseCommand):
    def handle(self, *args, **options):
        admin_group, _ = Group.objects.get_or_create(name='Admin')
        for user in User.objects.filter(is_superuser=True):
            user.groups.add(admin_group)
            self.stdout.write(f'Added {user.username} to Admin group')