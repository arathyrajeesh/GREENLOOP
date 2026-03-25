from django.db import migrations
from django.contrib.auth.hashers import make_password

def create_initial_superuser(apps, schema_editor):
    User = apps.get_model('users', 'User')
    email = "admin@greenloop.com"
    password = "admin135"  # As requested by the user
    
    if not User.objects.filter(email=email).exists():
        User.objects.create(
            email=email,
            password=make_password(password),
            name="System Admin",
            role="ADMIN",
            is_staff=True,
            is_superuser=True,
            is_active=True
        )

class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_initial_superuser),
    ]
