import uuid
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
            name='Pickup',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('location', django.contrib.gis.db.models.fields.PointField(help_text='GPS location of the pickup point', srid=4326)),
                ('waste_type', models.CharField(choices=[('dry', 'Dry Waste'), ('wet', 'Wet Waste'), ('hazardous', 'Hazardous Waste'), ('e-waste', 'E-Waste')], max_length=20)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('arrived', 'Arrived'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='pending', max_length=20)),
                ('scheduled_date', models.DateField(default=django.utils.timezone.now)),
                ('qr_code', models.CharField(blank=True, max_length=64, null=True, unique=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('resident', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pickups', to='users.user')),
                ('ward', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pickups', to='wards.ward')),
            ],
            options={
                'indexes': [models.Index(fields=['ward', 'scheduled_date', 'status'], name='pickup_ward_date_status_idx')],
            },
        ),
    ]
