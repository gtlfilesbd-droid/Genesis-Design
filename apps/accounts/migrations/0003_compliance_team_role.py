# Generated manually for SRS compliance workflow

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_user_avatar'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('designs', '0005_deadline_duration_and_notifications'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('design_requester', 'Design Requester'),
                    ('head_of_design', 'Head of Design'),
                    ('designer', 'Designer'),
                    ('verification_team', 'Verification Team'),
                    ('compliance_team', 'Compliance Team'),
                    ('admin', 'Admin'),
                ],
                default='design_requester',
                max_length=30,
            ),
        ),
    ]
