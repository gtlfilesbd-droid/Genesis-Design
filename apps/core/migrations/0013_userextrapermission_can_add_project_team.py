from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_userextrapermission_can_edit_project'),
    ]

    operations = [
        migrations.AddField(
            model_name='userextrapermission',
            name='can_add_project_team',
            field=models.BooleanField(default=False),
        ),
    ]
