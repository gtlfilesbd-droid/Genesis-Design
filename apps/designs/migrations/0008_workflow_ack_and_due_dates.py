from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('designs', '0007_submission_reference_metadata'),
    ]

    operations = [
        migrations.AddField(
            model_name='designrequest',
            name='compliance_acknowledged_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='designrequest',
            name='compliance_assigned_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='designrequest',
            name='compliance_due_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='designrequest',
            name='compliance_instructions',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='designrequest',
            name='verification_acknowledged_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='designrequest',
            name='verification_assigned_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='designrequest',
            name='verification_due_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='designrequest',
            name='verification_instructions',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='designrequest',
            name='status',
            field=models.CharField(
                choices=[
                    ('draft', 'Draft Request'),
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
