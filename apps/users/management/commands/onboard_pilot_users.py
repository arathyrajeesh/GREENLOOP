from django.core.management.base import BaseCommand
from apps.users.models import User
from apps.wards.models import Ward
import random

class Command(BaseCommand):
    help = "Onboard pilot HKS workers and residents"

    def handle(self, *args, **options):
        # Create 3 HKS Workers for Wards 1, 2, 3
        for i in range(1, 4):
            email = f"worker{i}@greenloop.org"
            ward = Ward.objects.filter(number=i).first()
            if not ward:
                self.stdout.write(self.style.WARNING(f"Ward {i} not found, skipping worker{i}"))
                continue
            
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "username": f"worker{i}",
                    "name": f"Worker {i} (HKS)",
                    "role": "HKS_WORKER",
                    "ward": ward,
                }
            )
            if created:
                user.set_password("GreenLoop@2026")
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Created worker: {email} in Ward {i}"))
            else:
                self.stdout.write(f"Worker {email} already exists")

        # Create 10 Residents for Wards 1-4
        for i in range(1, 11):
            email = f"resident{i}@example.com"
            # Distribute across Wards 1-4
            ward_num = (i % 4) + 1
            ward = Ward.objects.filter(number=ward_num).first()
            
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "username": f"resident{i}",
                    "name": f"Resident {i} (Pilot)",
                    "role": "RESIDENT",
                    "ward": ward,
                    "address": f"Kochi House #{i}, Ward {ward_num}",
                }
            )
            if created:
                user.set_password("GreenLoop@2026")
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Created resident: {email} in Ward {ward_num}"))
            else:
                self.stdout.write(f"Resident {email} already exists")

        self.stdout.write(self.style.SUCCESS("Pilot onboarding complete!"))
