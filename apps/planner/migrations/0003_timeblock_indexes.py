from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('planner', '0002_timeblock_scheduled_date'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='timeblock',
            options={
                'ordering': ('scheduled_date', 'start_time'),
            },
        ),
        migrations.AddIndex(
            model_name='timeblock',
            index=models.Index(fields=['user', 'scheduled_date'], name='planner_tim_user_id_dac284_idx'),
        ),
        migrations.AddIndex(
            model_name='timeblock',
            index=models.Index(fields=['user', 'day_of_week'], name='planner_tim_user_id_f02cd0_idx'),
        ),
    ]
