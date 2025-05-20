from django.db import models
from django.utils.translation import gettext_lazy as _

class Organization(models.Model):
    """Organization model for SentinelIQ system"""
    name = models.CharField(_('Name'), max_length=255)
    slug = models.SlugField(_('Slug'), unique=True)
    description = models.TextField(_('Description'), blank=True, null=True)
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated at'), auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = _('Organization')
        verbose_name_plural = _('Organizations')
        ordering = ['name']
