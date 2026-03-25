from django.db import migrations, models
import django.contrib.gis.db.models.fields
import django.contrib.postgres.indexes

class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Ward',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('number', models.PositiveIntegerField(unique=True)),
                ('location', django.contrib.gis.db.models.fields.PointField(help_text='Centroid of the ward', srid=4326)),
                ('boundary', django.contrib.gis.db.models.fields.PolygonField(help_text='Geographical boundary of the ward', srid=4326)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name_plural': 'Wards',
                'ordering': ['number'],
            },
        ),
        migrations.AddIndex(
            model_name='ward',
            index=django.contrib.postgres.indexes.GistIndex(fields=['boundary'], name='wards_ward_boundar_300e88_gist'),
        ),
    ]
