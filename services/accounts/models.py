from django.db import models
from django.contrib.auth.models import AbstractUser


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
    Custom user linked to an organization.
    """
    org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="users",
        null=True,
        blank=True,
    )

    # later: role, is_sales_rep, is_manager, etc.

    def __str__(self) -> str:
        if self.org:
            return f"{self.username} ({self.org.name})"
        return self.username
