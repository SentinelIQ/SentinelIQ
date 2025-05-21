from django.db import models
from django.utils.translation import gettext_lazy as _


class Case(models.Model):
    """Case model for organizations"""
    OPEN = 'open'
    IN_PROGRESS = 'in_progress'
    PENDING = 'pending'
    RESOLVED = 'resolved'
    CLOSED = 'closed'
    
    STATUS_CHOICES = [
        (OPEN, _('Open')),
        (IN_PROGRESS, _('In Progress')),
        (PENDING, _('Pending')),
        (RESOLVED, _('Resolved')),
        (CLOSED, _('Closed')),
    ]
    
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'
    
    PRIORITY_CHOICES = [
        (LOW, _('Low')),
        (MEDIUM, _('Medium')),
        (HIGH, _('High')),
        (CRITICAL, _('Critical')),
    ]
    
    # TLP (Traffic Light Protocol) choices
    TLP_WHITE = 'white'
    TLP_GREEN = 'green'
    TLP_AMBER = 'amber'
    TLP_RED = 'red'
    
    TLP_CHOICES = [
        (TLP_WHITE, _('TLP:WHITE')),
        (TLP_GREEN, _('TLP:GREEN')),
        (TLP_AMBER, _('TLP:AMBER')),
        (TLP_RED, _('TLP:RED')),
    ]
    
    # PAP (Permissible Actions Protocol) choices
    PAP_WHITE = 'white'
    PAP_GREEN = 'green'
    PAP_AMBER = 'amber'
    PAP_RED = 'red'
    
    PAP_CHOICES = [
        (PAP_WHITE, _('PAP:WHITE')),
        (PAP_GREEN, _('PAP:GREEN')),
        (PAP_AMBER, _('PAP:AMBER')),
        (PAP_RED, _('PAP:RED')),
    ]
    
    title = models.CharField(_('Title'), max_length=255)
    description = models.TextField(_('Description'))
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='cases',
    )
    priority = models.CharField(
        _('Priority'),
        max_length=10,
        choices=PRIORITY_CHOICES,
        default=MEDIUM,
    )
    status = models.CharField(
        _('Status'),
        max_length=15,
        choices=STATUS_CHOICES,
        default=OPEN,
    )
    assigned_to = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        related_name='assigned_cases',
        null=True,
        blank=True,
    )
    due_date = models.DateField(_('Due Date'), null=True, blank=True)
    related_alerts = models.ManyToManyField(
        'alerts.Alert',
        related_name='related_cases',
        blank=True,
    )
    tlp = models.CharField(
        _('TLP'),
        max_length=10,
        choices=TLP_CHOICES,
        default=TLP_AMBER,
        help_text=_('Traffic Light Protocol - Confidentiality of information'),
    )
    pap = models.CharField(
        _('PAP'),
        max_length=10,
        choices=PAP_CHOICES,
        default=PAP_AMBER,
        help_text=_('Permissible Actions Protocol - Level of exposure of information'),
    )
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated at'), auto_now=True)
    
    def __str__(self):
        return self.title
    
    def add_timeline_event(self, event_type, title, description='', user=None, old_value=None, new_value=None, metadata=None):
        """Add a timeline event to this case"""
        return CaseEvent.objects.create(
            case=self,
            event_type=event_type,
            title=title,
            description=description,
            user=user,
            old_value=old_value,
            new_value=new_value,
            metadata=metadata
        )
    
    def log_status_change(self, user, old_status, new_status):
        """Log a status change event"""
        old_display = dict(self.STATUS_CHOICES).get(old_status, old_status)
        new_display = dict(self.STATUS_CHOICES).get(new_status, new_status)
        
        return self.add_timeline_event(
            event_type=CaseEvent.STATUS_CHANGED,
            title=_('Status changed from {old} to {new}').format(old=old_display, new=new_display),
            user=user,
            old_value=old_status,
            new_value=new_status
        )
    
    def log_priority_change(self, user, old_priority, new_priority):
        """Log a priority change event"""
        old_display = dict(self.PRIORITY_CHOICES).get(old_priority, old_priority)
        new_display = dict(self.PRIORITY_CHOICES).get(new_priority, new_priority)
        
        return self.add_timeline_event(
            event_type=CaseEvent.PRIORITY_CHANGED,
            title=_('Priority changed from {old} to {new}').format(old=old_display, new=new_display),
            user=user,
            old_value=old_priority,
            new_value=new_priority
        )
    
    def log_assignee_change(self, user, old_assignee, new_assignee):
        """Log an assignee change event"""
        old_username = old_assignee.username if old_assignee else _('Unassigned')
        new_username = new_assignee.username if new_assignee else _('Unassigned')
        
        return self.add_timeline_event(
            event_type=CaseEvent.ASSIGNEE_CHANGED,
            title=_('Assignee changed from {old} to {new}').format(old=old_username, new=new_username),
            user=user,
            old_value=str(old_assignee.id) if old_assignee else None,
            new_value=str(new_assignee.id) if new_assignee else None
        )
    
    def log_due_date_change(self, user, old_date, new_date):
        """Log a due date change event"""
        return self.add_timeline_event(
            event_type=CaseEvent.DUE_DATE_CHANGED,
            title=_('Due date changed from {old} to {new}').format(
                old=old_date.strftime('%Y-%m-%d') if old_date else _('Not set'),
                new=new_date.strftime('%Y-%m-%d') if new_date else _('Not set')
            ),
            user=user,
            old_value=old_date.strftime('%Y-%m-%d') if old_date else None,
            new_value=new_date.strftime('%Y-%m-%d') if new_date else None
        )
    
    def log_comment_added(self, user, comment):
        """Log a comment added event"""
        return self.add_timeline_event(
            event_type=CaseEvent.COMMENT_ADDED,
            title=_('Comment added by {user}').format(user=user.username),
            description=comment.content[:100] + ('...' if len(comment.content) > 100 else ''),
            user=user,
            metadata={'comment_id': comment.id}
        )
    
    def log_attachment_added(self, user, attachment):
        """Log an attachment added event"""
        return self.add_timeline_event(
            event_type=CaseEvent.ATTACHMENT_ADDED,
            title=_('Attachment added by {user}').format(user=user.username),
            description=attachment.filename,
            user=user,
            metadata={'attachment_id': attachment.id}
        )
    
    def log_alert_linked(self, user, alert):
        """Log an alert linked event"""
        return self.add_timeline_event(
            event_type=CaseEvent.ALERT_LINKED,
            title=_('Alert linked: {alert}').format(alert=alert.title),
            user=user,
            metadata={'alert_id': alert.id}
        )
    
    def log_alert_unlinked(self, user, alert):
        """Log an alert unlinked event"""
        return self.add_timeline_event(
            event_type=CaseEvent.ALERT_UNLINKED,
            title=_('Alert unlinked: {alert}').format(alert=alert.title),
            user=user,
            metadata={'alert_id': alert.id}
        )
    
    def log_tlp_change(self, user, old_tlp, new_tlp):
        """Log a TLP change event"""
        old_display = dict(self.TLP_CHOICES).get(old_tlp, old_tlp)
        new_display = dict(self.TLP_CHOICES).get(new_tlp, new_tlp)
        
        return self.add_timeline_event(
            event_type=CaseEvent.TLP_CHANGED,
            title=_('TLP changed from {old} to {new}').format(old=old_display, new=new_display),
            user=user,
            old_value=old_tlp,
            new_value=new_tlp
        )
    
    def log_pap_change(self, user, old_pap, new_pap):
        """Log a PAP change event"""
        old_display = dict(self.PAP_CHOICES).get(old_pap, old_pap)
        new_display = dict(self.PAP_CHOICES).get(new_pap, new_pap)
        
        return self.add_timeline_event(
            event_type=CaseEvent.PAP_CHANGED,
            title=_('PAP changed from {old} to {new}').format(old=old_display, new=new_display),
            user=user,
            old_value=old_pap,
            new_value=new_pap
        )
    
    class Meta:
        verbose_name = _('Case')
        verbose_name_plural = _('Cases')
        ordering = ['-created_at']


class CaseComment(models.Model):
    """Comments on cases"""
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name='comments',
    )
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='case_comments',
    )
    content = models.TextField(_('Content'))
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    
    def __str__(self):
        return f'Comment on {self.case.title} by {self.user.username}'
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        result = super().save(*args, **kwargs)
        
        # Log timeline event for new comments
        if is_new and hasattr(self, 'case'):
            self.case.log_comment_added(self.user, self)
            
        return result
    
    class Meta:
        verbose_name = _('Case Comment')
        verbose_name_plural = _('Case Comments')
        ordering = ['-created_at']


class CaseAttachment(models.Model):
    """Attachments for cases"""
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name='attachments',
    )
    file = models.FileField(_('File'), upload_to='case_attachments/')
    filename = models.CharField(_('Filename'), max_length=255)
    uploaded_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='case_attachments',
    )
    uploaded_at = models.DateTimeField(_('Uploaded at'), auto_now_add=True)
    
    def __str__(self):
        return self.filename
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        result = super().save(*args, **kwargs)
        
        # Log timeline event for new attachments
        if is_new and hasattr(self, 'case'):
            self.case.log_attachment_added(self.uploaded_by, self)
            
        return result
    
    class Meta:
        verbose_name = _('Case Attachment')
        verbose_name_plural = _('Case Attachments')
        ordering = ['-uploaded_at']


class CaseEvent(models.Model):
    """Timeline events for cases"""
    CREATED = 'created'
    STATUS_CHANGED = 'status_changed'
    PRIORITY_CHANGED = 'priority_changed'
    ASSIGNEE_CHANGED = 'assignee_changed'
    DUE_DATE_CHANGED = 'due_date_changed'
    COMMENT_ADDED = 'comment_added'
    ATTACHMENT_ADDED = 'attachment_added'
    ALERT_LINKED = 'alert_linked'
    ALERT_UNLINKED = 'alert_unlinked'
    TLP_CHANGED = 'tlp_changed'
    PAP_CHANGED = 'pap_changed'
    CUSTOM = 'custom'
    
    EVENT_TYPE_CHOICES = [
        (CREATED, _('Case Created')),
        (STATUS_CHANGED, _('Status Changed')),
        (PRIORITY_CHANGED, _('Priority Changed')),
        (ASSIGNEE_CHANGED, _('Assignee Changed')),
        (DUE_DATE_CHANGED, _('Due Date Changed')),
        (COMMENT_ADDED, _('Comment Added')),
        (ATTACHMENT_ADDED, _('Attachment Added')),
        (ALERT_LINKED, _('Alert Linked')),
        (ALERT_UNLINKED, _('Alert Unlinked')),
        (TLP_CHANGED, _('TLP Changed')),
        (PAP_CHANGED, _('PAP Changed')),
        (CUSTOM, _('Custom Event')),
    ]
    
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name='timeline_events',
    )
    event_type = models.CharField(
        _('Event Type'),
        max_length=20,
        choices=EVENT_TYPE_CHOICES,
    )
    title = models.CharField(_('Event Title'), max_length=255)
    description = models.TextField(_('Event Description'), blank=True)
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        related_name='case_events',
        null=True,
        blank=True,
    )
    old_value = models.CharField(_('Old Value'), max_length=255, blank=True, null=True)
    new_value = models.CharField(_('New Value'), max_length=255, blank=True, null=True)
    metadata = models.JSONField(_('Metadata'), blank=True, null=True)
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    
    def __str__(self):
        return f"{self.get_event_type_display()} - {self.case.title}"
    
    def get_icon_class(self):
        """Return an icon class based on event type"""
        icon_map = {
            self.CREATED: 'fa-plus-circle text-success',
            self.STATUS_CHANGED: 'fa-exchange-alt text-info',
            self.PRIORITY_CHANGED: 'fa-level-up-alt text-warning',
            self.ASSIGNEE_CHANGED: 'fa-user-edit text-primary',
            self.DUE_DATE_CHANGED: 'fa-calendar-alt text-info',
            self.COMMENT_ADDED: 'fa-comment-dots text-secondary',
            self.ATTACHMENT_ADDED: 'fa-paperclip text-secondary',
            self.ALERT_LINKED: 'fa-link text-primary',
            self.ALERT_UNLINKED: 'fa-unlink text-danger',
            self.TLP_CHANGED: 'fa-shield-alt text-primary',
            self.PAP_CHANGED: 'fa-user-shield text-warning',
            self.CUSTOM: 'fa-star text-warning',
        }
        return icon_map.get(self.event_type, 'fa-circle')
    
    class Meta:
        verbose_name = _('Case Event')
        verbose_name_plural = _('Case Events')
        ordering = ['-created_at']
