import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils.translation import gettext_lazy as _

class UserManager(BaseUserManager):
    def create_user(self, email=None, username=None, password=None, **extra_fields):
        if not email and not username:
            raise ValueError(_("Either Email or Username must be set"))
        if email:
            email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "ADMIN")
        return self.create_user(email=email, password=password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ("ADMIN", "Admin"),
        ("RESIDENT", "Resident"),
        ("HKS_WORKER", "HKS Worker"),
        ("RECYCLER", "Recycler"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True, null=True, blank=True)
    email = models.EmailField(_("email address"), unique=True, db_index=True, null=True, blank=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    name = models.CharField(max_length=255, help_text="Supports Malayalam names")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="RESIDENT")
    ward = models.ForeignKey(
        "wards.Ward",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="users"
    )
    address = models.TextField(blank=True, help_text="User's residential or business address")
    fcm_token = models.CharField(max_length=255, null=True, blank=True, help_text="Firebase Cloud Messaging token for push notifications")

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    def __str__(self):
        return f"{self.email} ({self.name})"

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
