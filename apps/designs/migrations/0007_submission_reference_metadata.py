from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('designs', '0006_srs_compliance_workflow'),
        ('core', '0007_companysettings_file_sharing_policy'),
    ]

    operations = [
        migrations.AddField(
            model_name='designsubmission',
            name='file_name',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='designsubmission',
            name='revision_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='designsubmission',
            name='file',
            field=models.FileField(
                blank=True,
                help_text='Deprecated — reference-only storage; do not upload new files.',
                null=True,
                upload_to='design_submissions/%Y/%m/',
            ),
        ),
    ]
