"""
Accounts App — Models
━━━━━━━━━━━━━━━━━━━━
Custom User model with role-based access.
Roles: customer | staff | admin

Why custom user model?
  - We add 'role' field to every user
  - We add 'phone' for SMS notifications
  - We add 'loyalty_points' directly on user
  - Email is the login identifier (not username)
"""
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


class UserManager(BaseUserManager):
    """Custom manager — email is the unique identifier, not username."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email address is required')
        email = self.normalize_email(email)
        extra_fields.setdefault('role', 'customer')
        user = self.model(email=email, **extra_fields)
        user.set_password(password)  # bcrypt hashing handled by Django
        user.save(using=self._db)
        return user

    def create_staff_user(self, email, password=None, **extra_fields):
        extra_fields['role'] = 'staff'
        return self.create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields['role'] = 'admin'
        extra_fields['is_staff'] = True
        extra_fields['is_superuser'] = True
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    BrewMate User Model

    DB Table: accounts_user
    ┌──────────────────┬──────────────────────────────────────────┐
    │ Field            │ Description                              │
    ├──────────────────┼──────────────────────────────────────────┤
    │ email            │ Unique login identifier                  │
    │ role             │ customer / staff / admin                 │
    │ loyalty_points   │ Redeemable points balance                │
    │ phone            │ For SMS order notifications              │
    │ is_active        │ Soft delete — deactivate instead of del  │
    └──────────────────┴──────────────────────────────────────────┘
    """

    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('staff',    'Staff'),
        ('admin',    'Admin'),
    ]

    # Core fields
    email          = models.EmailField(unique=True)
    first_name     = models.CharField(max_length=50)
    last_name      = models.CharField(max_length=50, blank=True)
    phone          = models.CharField(max_length=15, blank=True)
    role           = models.CharField(max_length=10, choices=ROLE_CHOICES, default='customer')

    # Loyalty points (tracked here for quick access)
    loyalty_points = models.PositiveIntegerField(default=0)

    # Account status
    is_active      = models.BooleanField(default=True)
    is_staff       = models.BooleanField(default=False)
    date_joined    = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD  = 'email'  # Login with email
    REQUIRED_FIELDS = ['first_name']

    class Meta:
        db_table = 'accounts_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
        ]

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return f"{self.email} ({self.role})"

    @property
    def can_redeem_points(self):
        """100 points = 1 free coffee. Check if user can redeem."""
        return self.loyalty_points >= 100
