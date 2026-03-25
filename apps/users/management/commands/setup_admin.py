from django.core.management.base import BaseCommand
from apps.users.models import User

class Command(BaseCommand):
    help = "Create an admin superuser with specific credentials"

    def handle(self, *args, **options):
        email = "admin@greenloop.com"
        password = "admin135"
        name = "Admin User"
        
        if not User.objects.filter(email=email).exists():
            User.objects.create_superuser(
                email=email,
                password=password,
                name=name
            )
            self.stdout.write(self.style.SUCCESS(f"Successfully created superuser: {email}"))
        else:
            self.stdout.write(self.style.WARNING(f"Superuser {email} already exists."))
