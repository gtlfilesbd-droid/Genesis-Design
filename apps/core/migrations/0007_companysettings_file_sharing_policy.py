from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_userextrapermission'),
    ]

    operations = [
        migrations.AddField(
            model_name='companysettings',
            name='file_sharing_policy',
            field=models.TextField(
                blank=True,
                default=(
                    'Design files must be stored on the company internal file sharing system '
                    '(shared drive, BIM server, or CAD server). Genesis Design stores references only.'
                ),
                help_text='Shown on submit forms and design detail pages.',
            ),
        ),
    ]
