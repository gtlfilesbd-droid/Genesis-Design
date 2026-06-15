from django.db import migrations, models


def migrate_notification_type_sla_to_deadline(apps, schema_editor):
    Notification = apps.get_model('notifications', 'Notification')
    Notification.objects.filter(notification_type='sla').update(notification_type='deadline')


def migrate_notification_type_deadline_to_sla(apps, schema_editor):
    Notification = apps.get_model('notifications', 'Notification')
    Notification.objects.filter(notification_type='deadline').update(notification_type='sla')


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='notificationsetting',
            old_name='sla_warning_hours',
            new_name='deadline_warning_hours',
        ),
        migrations.RunPython(
            migrate_notification_type_sla_to_deadline,
            migrate_notification_type_deadline_to_sla,
        ),
        migrations.AlterField(
            model_name='notification',
            name='notification_type',
            field=models.CharField(
                choices=[
                    ('workflow', 'Workflow'),
                    ('deadline', 'Deadline'),
                    ('escalation', 'Escalation'),
                    ('system', 'System'),
                ],
                default='workflow',
                max_length=20,
            ),
        ),
    ]
