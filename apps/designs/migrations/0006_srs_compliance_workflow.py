import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('designs', '0005_deadline_duration_and_notifications'),
    ]

    operations = [
        migrations.AddField(
            model_name='designrequest',
            name='assigned_compliance_officer',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='compliance_assignments',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='designrequest',
            name='assigned_verifier',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='verifier_assignments',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='designrequest',
            name='approved_by_compliance',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='compliance_approvals',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='designrequest',
            name='compliance_skipped_by_hod',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='designrequest',
            name='verification_skipped_by_hod',
            field=models.BooleanField(default=False),
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
                    ('verification_pending', 'Verification Pending'),
                    ('verification_correction', 'Verification Correction'),
                    ('awaiting_compliance', 'Awaiting Compliance'),
                    ('compliance_pending', 'Compliance Pending'),
                    ('compliance_correction', 'Compliance Correction'),
                    ('final_approval_pending', 'Final Approval Pending'),
                    ('approved', 'Approved'),
                    ('completed', 'Completed'),
                    ('cancelled', 'Cancelled'),
                ],
                default='draft',
                max_length=30,
            ),
        ),
        migrations.CreateModel(
            name='ComplianceReview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(
                    choices=[('approved', 'Approved'), ('correction', 'Correction Required')],
                    max_length=20,
                )),
                ('comments', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('design', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='compliance_reviews',
                    to='designs.designrequest',
                )),
                ('reviewer', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='compliance_reviews_done',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
