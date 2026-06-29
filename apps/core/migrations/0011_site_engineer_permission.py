from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_deadlineconfiguration_action_sla'),
    ]

    operations = [
        migrations.AddField(
            model_name='deadlineconfiguration',
            name='action_engineer_acknowledge_days',
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='deadlineconfiguration',
            name='action_engineer_acknowledge_hours',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='userextrapermission',
            name='can_site_engineer',
            field=models.BooleanField(default=False),
        ),
    ]
