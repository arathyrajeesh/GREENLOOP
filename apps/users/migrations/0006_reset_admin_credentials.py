from django.db import migrations
from django.contrib.auth.hashers import make_password

def reset_admin_credentials(apps, schema_editor):
    User = apps.get_model('users', 'User')
    email = "admin@gmail.com"
    password = "GreenLoop@2026"
    
    # Update existing or create new admin
    user = User.objects.filter(email=email).first()
    if user:
        user.password = make_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.role = "ADMIN"
        user.save()
    else:
        User.objects.create(
            email=email,
            password=make_password(password),
            name="Admin User",
            role="ADMIN",
            is_staff=True,
            is_superuser=True,
            is_active=True
        )
    
    # Also ensure the old migration admin is still there but maybe updated or just leave it
    # The user said "reset to THIS email", so we prioritize admin@gmail.com

class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_user_fcm_token'),
    ]

    operations = [
        migrations.RunPython(reset_admin_credentials),
    ]
