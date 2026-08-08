import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('planner', '0003_timeblock_indexes'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='timeblock',
            name='description',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='timeblock',
            name='due_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='timeblock',
            name='status',
            field=models.CharField(
                choices=[
                    ('planned', 'Planned'),
                    ('in_progress', 'In progress'),
                    ('partial', 'Partial'),
                    ('completed', 'Completed'),
                    ('incomplete', 'Incomplete'),
                    ('abandoned', 'Abandoned'),
                    ('transferred', 'Transferred'),
                ],
                default='planned',
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name='ActivityEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('event_type', models.CharField(max_length=50)),
                ('payload', models.JSONField(default=dict)),
                ('actor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='planner_activity_events', to=settings.AUTH_USER_MODEL)),
                ('time_block', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='activity_events', to='planner.timeblock')),
            ],
            options={
                'ordering': ('-created_at', '-pk'),
            },
        ),
        migrations.AddIndex(
            model_name='activityevent',
            index=models.Index(fields=['time_block', '-created_at'], name='planner_act_time_bl_c91fde_idx'),
        ),
    ]
