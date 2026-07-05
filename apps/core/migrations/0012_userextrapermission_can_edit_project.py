from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_site_engineer_permission'),
    ]

    operations = [
        migrations.AddField(
            model_name='userextrapermission',
            name='can_edit_project',
            field=models.BooleanField(default=False),
        ),
    ]
