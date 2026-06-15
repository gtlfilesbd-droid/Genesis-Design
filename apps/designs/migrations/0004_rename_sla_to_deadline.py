import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('designs', '0003_designcomment_mentions_designrequest_primary_status_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='drawingtype',
            old_name='default_sla_days',
            new_name='allowed_days',
        ),
        migrations.RenameField(
            model_name='designrequest',
            old_name='sla_breached',
            new_name='deadline_missed',
        ),
        migrations.RenameField(
            model_name='designrequest',
            old_name='sla_start',
            new_name='deadline_start',
        ),
        migrations.RenameField(
            model_name='designrequest',
            old_name='sla_due',
            new_name='deadline_due',
        ),
        migrations.RenameField(
            model_name='designrequest',
            old_name='sla_status',
            new_name='deadline_status',
        ),
        migrations.AlterField(
            model_name='designrequest',
            name='deadline_status',
            field=models.CharField(
                choices=[
                    ('green', 'On Track'),
                    ('yellow', 'Deadline Warning'),
                    ('red', 'Deadline Missed'),
                ],
                default='green',
                max_length=10,
            ),
        ),
        migrations.RenameModel(
            old_name='SLARecord',
            new_name='DeadlineRecord',
        ),
        migrations.AlterField(
            model_name='deadlinerecord',
            name='design',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='deadline_record',
                to='designs.designrequest',
            ),
        ),
        migrations.AlterField(
            model_name='deadlinerecord',
            name='status',
            field=models.CharField(
                choices=[
                    ('green', 'On Track'),
                    ('yellow', 'Deadline Warning'),
                    ('red', 'Deadline Missed'),
                ],
                default='green',
                max_length=10,
            ),
        ),
    ]
