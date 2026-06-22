# core/management/commands/create_groups.py

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

class Command(BaseCommand):
    help = 'Create user groups: Student, Teacher, Admin'

    def handle(self, *args, **options):
        for name in ['Student', 'Teacher', 'Admin']:
            group, created = Group.objects.get_or_create(name=name)
            if created:
                self.stdout.write(f'Created group {name}')
            else:
                self.stdout.write(f'Group {name} already exists')