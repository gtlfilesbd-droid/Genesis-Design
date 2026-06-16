from django.core.management.base import BaseCommand

from apps.core.settings_forms import ensure_role_permissions


class Command(BaseCommand):
    help = 'Seed role permission defaults (Settings → Role Permissions matrix)'

    def handle(self, *args, **options):
        ensure_role_permissions()
        from django.core.management import call_command
        call_command('sync_auth_groups')
        self.stdout.write(self.style.SUCCESS(
            'Role permissions synced from defaults. '
            'Adjust access in Settings -> Role Permissions.'
        ))
