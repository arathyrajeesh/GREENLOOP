from django.db import migrations, models
import django.db.models.deletion
import django.contrib.gis.db.models.fields
import django.utils.timezone

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('users', '0001_initial'),
        ('wards', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Route',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('route_date', models.DateField(default=django.utils.timezone.now)),
                ('planned_path', django.contrib.gis.db.models.fields.LineStringField(help_text='Planned collection path', srid=4326)),
                ('actual_path', django.contrib.gis.db.models.fields.LineStringField(blank=True, help_text='Actual GPS track', null=True, srid=4326)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('hks_worker', models.ForeignKey(limit_choices_to={'role': 'HKS_WORKER'}, on_delete=django.db.models.deletion.CASCADE, related_name='routes', to='users.user')),
                ('ward', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='routes', to='wards.ward')),
            ],
            options={
                'indexes': [models.Index(fields=['hks_worker', 'route_date'], name='route_worker_date_idx')],
            },
        ),
    ]
