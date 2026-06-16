from django.db import migrations, models


def seed_compliance_role_defaults(apps, schema_editor):
    RolePermission = apps.get_model('core', 'RolePermission')
    defaults = {
        'admin': {
            'can_compliance': True,
        },
        'compliance_team': {
            'can_create_project': False,
            'can_create_request': False,
            'can_assign_designer': False,
            'can_review': False,
            'can_verify': False,
            'can_compliance': True,
            'can_manage_users': False,
            'can_view_reports': False,
            'can_manage_settings': False,
        },
    }
    for role, fields in defaults.items():
        RolePermission.objects.update_or_create(role=role, defaults=fields)
    RolePermission.objects.filter(role='compliance_team').update(can_compliance=True)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_deadline_configuration_hours'),
        ('accounts', '0003_compliance_team_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='rolepermission',
            name='can_compliance',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(seed_compliance_role_defaults, migrations.RunPython.noop),
    ]
