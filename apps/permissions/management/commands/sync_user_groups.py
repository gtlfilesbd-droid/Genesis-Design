from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.accounts.signals import sync_user_group_and_permissions


class Command(BaseCommand):
    help = "Bulk sync all users into role groups (and extra perms into user_permissions)"

    def handle(self, *args, **options):
        count = 0
        for user in User.objects.all().iterator():
            sync_user_group_and_permissions(user)
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Synced {count} users"))

