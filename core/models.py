from django.db import models
from django.utils.translation import gettext_lazy as _

# Create your models here.

class Tag(models.Model):
    """Tag model for categorizing alerts and cases"""
    name = models.CharField(_('Name'), max_length=50, unique=True)
    color = models.CharField(_('Color'), max_length=20, default='primary')
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = _('Tag')
        verbose_name_plural = _('Tags')
        ordering = ['name']
