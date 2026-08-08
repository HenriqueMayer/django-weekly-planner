from datetime import date, timedelta

from django.db import migrations, models


def assign_current_week(apps, schema_editor):
    TimeBlock = apps.get_model('planner', 'TimeBlock')
    current = date.today()
    monday = current - timedelta(days=current.weekday())
    for block in TimeBlock.objects.all().iterator():
        block.scheduled_date = monday + timedelta(days=block.day_of_week)
        block.save(update_fields=['scheduled_date'])


class Migration(migrations.Migration):
    dependencies = [
        ('planner', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='timeblock',
            name='scheduled_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.RunPython(assign_current_week, migrations.RunPython.noop),
    ]
