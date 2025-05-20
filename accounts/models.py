from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    """Custom user model that extends AbstractUser"""
    SUPERADMIN = 'superadmin'
    ORG_ADMIN = 'org_admin'
    ANALYST = 'analyst'
    
    ROLE_CHOICES = [
        (SUPERADMIN, 'Super Admin'),
        (ORG_ADMIN, 'Organization Admin'),
        (ANALYST, 'Analyst'),
    ]
    
    role = models.CharField(
        _('Role'),
        max_length=20,
        choices=ROLE_CHOICES,
        default=ANALYST,
    )
    
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='users',
        null=True,
        blank=True,
    )
    
    groups = models.ManyToManyField(
        Group,
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name="custom_user_set",
        related_query_name="user",
    )
    
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name="custom_user_set",
        related_query_name="user",
    )
    
    def is_superadmin(self):
        return self.role == self.SUPERADMIN
    
    def is_org_admin(self):
        return self.role == self.ORG_ADMIN
    
    def is_analyst(self):
        return self.role == self.ANALYST
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
