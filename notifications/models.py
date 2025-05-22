from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import json
import uuid


class NotificationDestination(models.Model):
    """Destination for notifications - where notifications will be sent"""
    EMAIL = 'email'
    WEBHOOK = 'webhook'
    SLACK = 'slack'
    MATTERMOST = 'mattermost'
    CUSTOM_HTTP = 'custom_http'
    
    TYPE_CHOICES = [
        (EMAIL, _('Email')),
        (WEBHOOK, _('Webhook')),
        (SLACK, _('Slack')),
        (MATTERMOST, _('Mattermost')),
        (CUSTOM_HTTP, _('Custom HTTP Request')),
    ]
    
    # Dictionary for easy lookup
    TYPE_CHOICES_DICT = dict(TYPE_CHOICES)
    
    name = models.CharField(_('Name'), max_length=100)
    type = models.CharField(_('Type'), max_length=20, choices=TYPE_CHOICES)
    config = models.JSONField(_('Configuration'), help_text=_('JSON configuration for the destination'))
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='notification_destinations',
    )
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated at'), auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"
    
    class Meta:
        verbose_name = _('Notification Destination')
        verbose_name_plural = _('Notification Destinations')
        ordering = ['name']
        unique_together = [['name', 'organization']]


class NotificationRule(models.Model):
    """Rules for when to trigger notifications"""
    # Event sources
    ALERT = 'alert'
    CASE = 'case'
    TASK = 'task'
    OBSERVABLE = 'observable'
    SYSTEM = 'system'
    
    SOURCE_CHOICES = [
        (ALERT, _('Alert')),
        (CASE, _('Case')),
        (TASK, _('Task')),
        (OBSERVABLE, _('Observable')),
        (SYSTEM, _('System')),
    ]
    
    # Dictionary for easy lookup
    SOURCE_CHOICES_DICT = dict(SOURCE_CHOICES)
    
    # Common events
    CREATED = 'created'
    UPDATED = 'updated'
    DELETED = 'deleted'
    STATUS_CHANGED = 'status_changed'
    ASSIGNED = 'assigned'
    
    # Alert specific events
    ALERT_SEVERITY_CHANGED = 'alert_severity_changed'
    ALERT_ESCALATED = 'alert_escalated'
    
    # Case specific events
    CASE_PRIORITY_CHANGED = 'case_priority_changed'
    CASE_COMMENT_ADDED = 'case_comment_added'
    CASE_ATTACHMENT_ADDED = 'case_attachment_added'
    
    # Task specific events
    TASK_COMPLETED = 'task_completed'
    TASK_OVERDUE = 'task_overdue'
    
    # Observable specific events
    OBSERVABLE_MALICIOUS_ADDED = 'observable_malicious_added'
    OBSERVABLE_ENRICHED = 'observable_enriched'
    
    # System events
    SYSTEM_DATABASE_BACKUP = 'system_database_backup'
    SYSTEM_ERROR = 'system_error'
    SYSTEM_USER_LOGIN_FAILED = 'system_user_login_failed'
    
    EVENT_CHOICES = [
        # Common events
        (CREATED, _('Created')),
        (UPDATED, _('Updated')),
        (DELETED, _('Deleted')),
        (STATUS_CHANGED, _('Status Changed')),
        (ASSIGNED, _('Assigned')),
        
        # Alert specific events
        (ALERT_SEVERITY_CHANGED, _('Severity Changed')),
        (ALERT_ESCALATED, _('Escalated to Case')),
        
        # Case specific events
        (CASE_PRIORITY_CHANGED, _('Priority Changed')),
        (CASE_COMMENT_ADDED, _('Comment Added')),
        (CASE_ATTACHMENT_ADDED, _('Attachment Added')),
        
        # Task specific events
        (TASK_COMPLETED, _('Task Completed')),
        (TASK_OVERDUE, _('Task Overdue')),
        
        # Observable specific events
        (OBSERVABLE_MALICIOUS_ADDED, _('Malicious Observable Added')),
        (OBSERVABLE_ENRICHED, _('Observable Enriched')),
        
        # System events
        (SYSTEM_DATABASE_BACKUP, _('Database Backup Completed')),
        (SYSTEM_ERROR, _('System Error')),
        (SYSTEM_USER_LOGIN_FAILED, _('User Login Failed')),
    ]
    
    # Dictionary for easy lookup
    EVENT_CHOICES_DICT = dict(EVENT_CHOICES)
    
    name = models.CharField(_('Name'), max_length=100)
    description = models.TextField(_('Description'), blank=True)
    source = models.CharField(_('Source'), max_length=20, choices=SOURCE_CHOICES)
    event_type = models.CharField(_('Event Type'), max_length=50, choices=EVENT_CHOICES)
    conditions = models.JSONField(
        _('Conditions'), 
        default=dict,
        blank=True,
        help_text=_('JSON conditions that must be met to trigger notification')
    )
    destinations = models.ManyToManyField(
        NotificationDestination,
        verbose_name=_('Destinations'),
        related_name='rules',
    )
    template_subject = models.CharField(
        _('Template Subject'), 
        max_length=255, 
        blank=True,
        help_text=_('Template for notification subject with variables like {{case.title}}')
    )
    template_body = models.TextField(
        _('Template Body'), 
        blank=True,
        help_text=_('Template for notification body with variables like {{case.description}}')
    )
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='notification_rules',
    )
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated at'), auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_source_display()} - {self.get_event_type_display()})"
    
    class Meta:
        verbose_name = _('Notification Rule')
        verbose_name_plural = _('Notification Rules')
        ordering = ['source', 'event_type', 'name']
        unique_together = [['name', 'organization']]


class NotificationLog(models.Model):
    """Log of notifications sent"""
    SUCCESS = 'success'
    FAILED = 'failed'
    PENDING = 'pending'
    
    STATUS_CHOICES = [
        (SUCCESS, _('Success')),
        (FAILED, _('Failed')),
        (PENDING, _('Pending')),
    ]
    
    # Dictionary for easy lookup
    STATUS_CHOICES_DICT = dict(STATUS_CHOICES)
    
    rule = models.ForeignKey(
        NotificationRule,
        on_delete=models.SET_NULL,
        related_name='logs',
        null=True,
        verbose_name=_('Notification Rule'),
    )
    destination = models.ForeignKey(
        NotificationDestination,
        on_delete=models.SET_NULL,
        related_name='logs',
        null=True,
        verbose_name=_('Destination'),
    )
    event_data = models.JSONField(_('Event Data'), default=dict, blank=True)
    status = models.CharField(_('Status'), max_length=10, choices=STATUS_CHOICES, default=PENDING)
    subject = models.CharField(_('Subject'), max_length=255)
    body = models.TextField(_('Body'))
    error_message = models.TextField(_('Error Message'), blank=True)
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    sent_at = models.DateTimeField(_('Sent at'), null=True, blank=True)
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='notification_logs',
    )
    tracking_id = models.UUIDField(_('Tracking ID'), default=uuid.uuid4, editable=False)
    
    def __str__(self):
        return f"Notification for {self.rule} - {self.get_status_display()}"
    
    def mark_as_sent(self):
        """Mark this notification as successfully sent"""
        self.status = self.SUCCESS
        self.sent_at = timezone.now()
        self.save()
    
    def mark_as_failed(self, error_message):
        """Mark this notification as failed"""
        self.status = self.FAILED
        self.error_message = error_message
        self.save()
    
    class Meta:
        verbose_name = _('Notification Log')
        verbose_name_plural = _('Notification Logs')
        ordering = ['-created_at']


class NotificationEvent(models.Model):
    """Event for notification tracking"""
    source_id = models.CharField(_('Source ID'), max_length=50)
    source_type = models.CharField(_('Source Type'), max_length=50)
    event_type = models.CharField(_('Event Type'), max_length=50)
    event_data = models.JSONField(_('Event Data'), default=dict)
    processed = models.BooleanField(_('Processed'), default=False)
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='notification_events',
    )
    
    def __str__(self):
        return f"{self.source_type} {self.event_type} event on {self.created_at}"
    
    class Meta:
        verbose_name = _('Notification Event')
        verbose_name_plural = _('Notification Events')
        ordering = ['-created_at']
