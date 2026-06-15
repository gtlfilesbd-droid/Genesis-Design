from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_rename_sla_to_deadline'),
    ]

    operations = [
        migrations.AddField(
            model_name='deadlineconfiguration',
            name='escalation_level_1_hours',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='deadlineconfiguration',
            name='escalation_level_2_hours',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='deadlineconfiguration',
            name='escalation_level_3_days',
            field=models.PositiveSmallIntegerField(default=4),
        ),
        migrations.AddField(
            model_name='deadlineconfiguration',
            name='escalation_level_3_hours',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='deadlineconfiguration',
            name='escalation_level_4_days',
            field=models.PositiveSmallIntegerField(default=5),
        ),
        migrations.AddField(
            model_name='deadlineconfiguration',
            name='escalation_level_4_hours',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='deadlineconfiguration',
            name='auto_breach_notify',
            field=models.BooleanField(
                default=True,
                help_text='Send a notification when a design first misses its deadline.',
            ),
        ),
        migrations.AlterField(
            model_name='deadlineconfiguration',
            name='count_weekends',
            field=models.BooleanField(
                default=False,
                help_text='Count only weekdays when calculating deadline due dates.',
            ),
        ),
        migrations.AlterField(
            model_name='deadlineconfiguration',
            name='default_warning_percent',
            field=models.PositiveSmallIntegerField(
                default=20,
                help_text='Show warning when this percent of the allowed time remains.',
            ),
        ),
    ]
