from django.db import migrations, models


def copy_review_cancel_reasons(apps, schema_editor):
    DesignRequest = apps.get_model('designs', 'DesignRequest')
    for design in DesignRequest.objects.exclude(review_cancel_reason='').iterator():
        design.cancel_reason = design.review_cancel_reason
        design.save(update_fields=['cancel_reason'])


class Migration(migrations.Migration):

    dependencies = [
        ('designs', '0011_request_under_review_routing'),
    ]

    operations = [
        migrations.AddField(
            model_name='designrequest',
            name='cancel_reason',
            field=models.TextField(blank=True),
        ),
        migrations.RunPython(copy_review_cancel_reasons, migrations.RunPython.noop),
    ]
