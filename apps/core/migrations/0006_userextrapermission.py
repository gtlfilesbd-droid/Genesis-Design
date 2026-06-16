from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0005_rolepermission_can_compliance'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserExtraPermission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('can_create_project', models.BooleanField(default=False)),
                ('can_create_request', models.BooleanField(default=False)),
                ('can_assign_designer', models.BooleanField(default=False)),
                ('can_review', models.BooleanField(default=False)),
                ('can_verify', models.BooleanField(default=False)),
                ('can_compliance', models.BooleanField(default=False)),
                ('can_manage_users', models.BooleanField(default=False)),
                ('can_view_reports', models.BooleanField(default=False)),
                ('can_manage_settings', models.BooleanField(default=False)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='extra_permissions',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name_plural': 'user extra permissions',
            },
        ),
    ]
