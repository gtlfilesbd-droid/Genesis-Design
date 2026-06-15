from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('designs', '0004_rename_sla_to_deadline'),
    ]

    operations = [
        migrations.AddField(
            model_name='drawingtype',
            name='allowed_hours',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='deadlinerecord',
            name='breach_notified_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='deadlinerecord',
            name='warning_notified_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
