from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('designs', '0009_designrequest_action_sla_breach'),
    ]

    operations = [
        migrations.AddField(
            model_name='designrequest',
            name='assigned_site_engineer',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='site_engineer_assignments',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='designrequest',
            name='engineer_acknowledged_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='designrequest',
            name='engineer_assigned_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='designrequest',
            name='engineer_due_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='designrequest',
            name='engineer_instructions',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='designrequest',
            name='engineer_site_notes',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='designrequest',
            name='engineer_submitted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='designrequest',
            name='status',
            field=models.CharField(
                choices=[
                    ('draft', 'Draft Request'),
                    ('engineer_pending_acknowledgement', 'Engineer Pending Acknowledgement'),
                    ('engineer_in_progress', 'Engineer In Progress'),
                    ('new_request', 'New Request'),
                    ('acknowledged', 'Acknowledged'),
                    ('assigned', 'Assigned'),
                    ('in_progress', 'In Progress'),
                    ('submitted', 'Submitted'),
                    ('under_review', 'Under Review'),
                    ('correction_required', 'Correction Required'),
                    ('resubmitted', 'Re-Submitted'),
                    ('verification_pending_acknowledgement', 'Verification Pending Acknowledgement'),
                    ('verification_pending', 'Verification Pending'),
                    ('verification_correction', 'Verification Correction'),
                    ('awaiting_compliance', 'Awaiting Compliance'),
                    ('compliance_pending_acknowledgement', 'Compliance Pending Acknowledgement'),
                    ('compliance_pending', 'Compliance Pending'),
                    ('compliance_correction', 'Compliance Correction'),
                    ('final_approval_pending', 'Final Approval Pending'),
                    ('approved', 'Approved'),
                    ('completed', 'Completed'),
                    ('cancelled', 'Cancelled'),
                ],
                default='draft',
                max_length=40,
            ),
        ),
    ]
