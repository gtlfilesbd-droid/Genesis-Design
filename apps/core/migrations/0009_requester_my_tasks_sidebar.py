from django.db import migrations


def enable_requester_my_tasks(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    UserSidebarPermission = apps.get_model('core', 'UserSidebarPermission')
    requester_role = 'design_requester'

    for user in User.objects.filter(role=requester_role).iterator():
        sidebar, _ = UserSidebarPermission.objects.get_or_create(
            user=user,
            defaults={'nav_my_tasks': True},
        )
        if not sidebar.nav_my_tasks:
            sidebar.nav_my_tasks = True
            sidebar.save(update_fields=['nav_my_tasks'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_usersidebarpermission'),
        ('accounts', '0003_compliance_team_role'),
    ]

    operations = [
        migrations.RunPython(enable_requester_my_tasks, noop),
    ]
