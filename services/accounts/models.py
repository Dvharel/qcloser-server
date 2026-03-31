from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models


class EmailUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        email = email.lower().strip() if email else ""
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        if "org" not in extra_fields and "org_id" not in extra_fields:
            org, _ = Organization.objects.get_or_create(name="Default")
            extra_fields["org"] = org
        return self.create_user(email, password, **extra_fields)


class Organization(models.Model):
    """
    A company / team using the system.
    Multi-tenant root object.
    """
    name = models.CharField(max_length=255)
    domain = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional: email domain like 'acme.com' for future auto-org matching.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class User(AbstractUser):
    """
    Custom user linked to an organization. Login is by email + password.
    """
    username = None
    email = models.EmailField("email address", unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = EmailUserManager()

    org = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="users",
    )

    # later: role, is_sales_rep, is_manager, etc.

    def save(self, *args, **kwargs):
        self.email = self.email.lower().strip()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.email} ({self.org.name})"
