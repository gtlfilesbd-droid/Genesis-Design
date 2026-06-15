from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_companysettings_rolepermission_slaconfiguration'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='SLAConfiguration',
            new_name='DeadlineConfiguration',
        ),
        migrations.AlterModelOptions(
            name='deadlineconfiguration',
            options={'verbose_name_plural': 'Deadline configuration'},
        ),
    ]
