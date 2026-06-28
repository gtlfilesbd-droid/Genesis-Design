from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('designs', '0008_workflow_ack_and_due_dates'),
    ]

    operations = [
        migrations.AddField(
            model_name='designrequest',
            name='action_sla_breached_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='designrequest',
            name='action_sla_breach_status',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
    ]
