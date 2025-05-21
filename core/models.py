from django.db import models
from django.utils.translation import gettext_lazy as _

# Create your models here.

class Tag(models.Model):
    """Tag model for categorizing alerts and cases"""
    
    # Color choices for tags
    PRIMARY = 'primary'
    SECONDARY = 'secondary'
    SUCCESS = 'success'
    DANGER = 'danger'
    WARNING = 'warning'
    INFO = 'info'
    LIGHT = 'light'
    DARK = 'dark'
    
    COLOR_CHOICES = [
        (PRIMARY, _('Blue')),
        (SECONDARY, _('Gray')),
        (SUCCESS, _('Green')),
        (DANGER, _('Red')),
        (WARNING, _('Yellow')),
        (INFO, _('Light Blue')),
        (LIGHT, _('White')),
        (DARK, _('Black')),
    ]
    
    name = models.CharField(_('Name'), max_length=50)
    color = models.CharField(
        _('Color'),
        max_length=20,
        choices=COLOR_CHOICES,
        default=PRIMARY,
    )
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = _('Tag')
        verbose_name_plural = _('Tags')
        ordering = ['name']


class Observable(models.Model):
    """Observable model for IOCs (Indicators of Compromise)"""
    
    # Type choices for observables
    IP_ADDRESS = 'ip_address'
    DOMAIN = 'domain'
    URL = 'url'
    EMAIL = 'email'
    HASH_MD5 = 'hash_md5'
    HASH_SHA1 = 'hash_sha1'
    HASH_SHA256 = 'hash_sha256'
    FILENAME = 'filename'
    REGISTRY_KEY = 'registry_key'
    USER_AGENT = 'user_agent'
    PROCESS_NAME = 'process_name'
    MUTEX = 'mutex'
    CVE = 'cve'
    OTHER = 'other'
    
    TYPE_CHOICES = [
        (IP_ADDRESS, _('IP Address')),
        (DOMAIN, _('Domain')),
        (URL, _('URL')),
        (EMAIL, _('Email')),
        (HASH_MD5, _('MD5 Hash')),
        (HASH_SHA1, _('SHA1 Hash')),
        (HASH_SHA256, _('SHA256 Hash')),
        (FILENAME, _('Filename')),
        (REGISTRY_KEY, _('Registry Key')),
        (USER_AGENT, _('User Agent')),
        (PROCESS_NAME, _('Process Name')),
        (MUTEX, _('Mutex')),
        (CVE, _('CVE')),
        (OTHER, _('Other')),
    ]
    
    # Confidence levels for observables
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    
    CONFIDENCE_CHOICES = [
        (LOW, _('Low')),
        (MEDIUM, _('Medium')),
        (HIGH, _('High')),
    ]
    
    value = models.CharField(_('Value'), max_length=255)
    type = models.CharField(
        _('Type'),
        max_length=20,
        choices=TYPE_CHOICES,
        default=OTHER,
    )
    description = models.TextField(_('Description'), blank=True)
    confidence = models.CharField(
        _('Confidence'),
        max_length=10,
        choices=CONFIDENCE_CHOICES,
        default=MEDIUM,
    )
    is_malicious = models.BooleanField(_('Is Malicious'), default=False)
    first_seen = models.DateTimeField(_('First Seen'), auto_now_add=True)
    last_seen = models.DateTimeField(_('Last Seen'), auto_now=True)
    
    # Relationships to Alert and Case models will be defined on those models
    # using ManyToManyField
    
    def __str__(self):
        return f"{self.get_type_display()}: {self.value}"
    
    class Meta:
        verbose_name = _('Observable')
        verbose_name_plural = _('Observables')
        ordering = ['-last_seen']
        unique_together = ['value', 'type']  # Prevent duplicate observables of the same type
