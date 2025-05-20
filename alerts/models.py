from django.db import models
from django.utils.translation import gettext_lazy as _

class Alert(models.Model):
    """Alert model for organizations"""
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'
    
    SEVERITY_CHOICES = [
        (LOW, _('Low')),
        (MEDIUM, _('Medium')),
        (HIGH, _('High')),
        (CRITICAL, _('Critical')),
    ]
    
    NEW = 'new'
    ACKNOWLEDGED = 'acknowledged'
    IN_PROGRESS = 'in_progress'
    RESOLVED = 'resolved'
    CLOSED = 'closed'
    
    STATUS_CHOICES = [
        (NEW, _('New')),
        (ACKNOWLEDGED, _('Acknowledged')),
        (IN_PROGRESS, _('In Progress')),
        (RESOLVED, _('Resolved')),
        (CLOSED, _('Closed')),
    ]
    
    title = models.CharField(_('Title'), max_length=255)
    description = models.TextField(_('Description'))
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='alerts',
    )
    severity = models.CharField(
        _('Severity'),
        max_length=10,
        choices=SEVERITY_CHOICES,
        default=MEDIUM,
    )
    status = models.CharField(
        _('Status'),
        max_length=15,
        choices=STATUS_CHOICES,
        default=NEW,
    )
    assigned_to = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        related_name='assigned_alerts',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated at'), auto_now=True)
    
    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name = _('Alert')
        verbose_name_plural = _('Alerts')
        ordering = ['-created_at']
