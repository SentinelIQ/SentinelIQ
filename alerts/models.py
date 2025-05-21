from django.db import models
from django.utils.translation import gettext_lazy as _

class AlertEvent(models.Model):
    """Timeline events for alerts"""
    CREATED = 'created'
    STATUS_CHANGED = 'status_changed'
    SEVERITY_CHANGED = 'severity_changed'
    ASSIGNEE_CHANGED = 'assignee_changed'
    TLP_CHANGED = 'tlp_changed'
    PAP_CHANGED = 'pap_changed'
    TAGS_CHANGED = 'tags_changed'
    OBSERVABLE_ADDED = 'observable_added'
    OBSERVABLE_REMOVED = 'observable_removed'
    COMMENT_ADDED = 'comment_added'
    RELATED_ALERT_ADDED = 'related_alert_added'
    RELATED_ALERT_REMOVED = 'related_alert_removed'
    ESCALATED = 'escalated'
    MITRE_ATTACK_ADDED = 'mitre_attack_added'
    MITRE_ATTACK_REMOVED = 'mitre_attack_removed'
    CUSTOM = 'custom'
    
    EVENT_TYPE_CHOICES = [
        (CREATED, _('Alert Created')),
        (STATUS_CHANGED, _('Status Changed')),
        (SEVERITY_CHANGED, _('Severity Changed')),
        (ASSIGNEE_CHANGED, _('Assignee Changed')),
        (TLP_CHANGED, _('TLP Changed')),
        (PAP_CHANGED, _('PAP Changed')),
        (TAGS_CHANGED, _('Tags Changed')),
        (OBSERVABLE_ADDED, _('Observable Added')),
        (OBSERVABLE_REMOVED, _('Observable Removed')),
        (COMMENT_ADDED, _('Comment Added')),
        (RELATED_ALERT_ADDED, _('Related Alert Added')),
        (RELATED_ALERT_REMOVED, _('Related Alert Removed')),
        (ESCALATED, _('Escalated to Case')),
        (MITRE_ATTACK_ADDED, _('MITRE ATT&CK Added')),
        (MITRE_ATTACK_REMOVED, _('MITRE ATT&CK Removed')),
        (CUSTOM, _('Custom Event')),
    ]
    
    alert = models.ForeignKey(
        'Alert',
        on_delete=models.CASCADE,
        related_name='timeline_events',
    )
    event_type = models.CharField(
        _('Event Type'),
        max_length=25,
        choices=EVENT_TYPE_CHOICES,
        default=CREATED
    )
    title = models.CharField(_('Event Title'), max_length=255)
    description = models.TextField(_('Event Description'), blank=True)
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        related_name='alert_events',
        null=True,
        blank=True,
    )
    old_value = models.CharField(_('Old Value'), max_length=255, blank=True, null=True)
    new_value = models.CharField(_('New Value'), max_length=255, blank=True, null=True)
    metadata = models.JSONField(_('Metadata'), blank=True, null=True)
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    
    def __str__(self):
        return f"{self.get_event_type_display()} - {self.alert.title}"
    
    def get_icon_class(self):
        """Return an icon class based on event type"""
        icon_map = {
            self.CREATED: 'fa-plus-circle text-success',
            self.STATUS_CHANGED: 'fa-exchange-alt text-info',
            self.SEVERITY_CHANGED: 'fa-level-up-alt text-warning',
            self.ASSIGNEE_CHANGED: 'fa-user-edit text-primary',
            self.TLP_CHANGED: 'fa-shield-alt text-primary',
            self.PAP_CHANGED: 'fa-user-shield text-warning',
            self.TAGS_CHANGED: 'fa-tags text-info',
            self.OBSERVABLE_ADDED: 'fa-eye text-success',
            self.OBSERVABLE_REMOVED: 'fa-eye-slash text-danger',
            self.COMMENT_ADDED: 'fa-comment-dots text-secondary',
            self.RELATED_ALERT_ADDED: 'fa-plus-circle text-success',
            self.RELATED_ALERT_REMOVED: 'fa-minus-circle text-danger',
            self.ESCALATED: 'fa-arrow-up text-success',
            self.MITRE_ATTACK_ADDED: 'fa-plus-circle text-success',
            self.MITRE_ATTACK_REMOVED: 'fa-minus-circle text-danger',
            self.CUSTOM: 'fa-star text-warning',
        }
        return icon_map.get(self.event_type, 'fa-circle')
    
    class Meta:
        verbose_name = _('Alert Event')
        verbose_name_plural = _('Alert Events')
        ordering = ['-created_at']

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
    tags = models.ManyToManyField(
        'core.Tag',
        verbose_name=_('Tags'),
        related_name='alerts',
        blank=True,
    )
    observables = models.ManyToManyField(
        'core.Observable',
        verbose_name=_('Observables'),
        related_name='alerts',
        blank=True,
    )
    related_alerts = models.ManyToManyField(
        'self',
        verbose_name=_('Related Alerts'),
        symmetrical=True,
        blank=True,
        help_text=_('Alerts that are related or similar to this one')
    )
    # MITRE ATT&CK relations
    mitre_tactics = models.ManyToManyField(
        'core.MitreTactic',
        verbose_name=_('MITRE Tactics'),
        related_name='alerts',
        blank=True,
    )
    mitre_techniques = models.ManyToManyField(
        'core.MitreTechnique',
        verbose_name=_('MITRE Techniques'),
        related_name='alerts',
        blank=True,
    )
    mitre_subtechniques = models.ManyToManyField(
        'core.MitreSubTechnique',
        verbose_name=_('MITRE Sub-techniques'),
        related_name='alerts',
        blank=True,
    )
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated at'), auto_now=True)
    
    def add_timeline_event(self, event_type, title, description='', user=None, old_value=None, new_value=None, metadata=None):
        """Add a timeline event to this alert"""
        return AlertEvent.objects.create(
            alert=self,
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
            event_type=AlertEvent.STATUS_CHANGED,
            title=_('Status changed from {old} to {new}').format(old=old_display, new=new_display),
            user=user,
            old_value=old_status,
            new_value=new_status
        )
    
    def log_severity_change(self, user, old_severity, new_severity):
        """Log a severity change event"""
        old_display = dict(self.SEVERITY_CHOICES).get(old_severity, old_severity)
        new_display = dict(self.SEVERITY_CHOICES).get(new_severity, new_severity)
        
        return self.add_timeline_event(
            event_type=AlertEvent.SEVERITY_CHANGED,
            title=_('Severity changed from {old} to {new}').format(old=old_display, new=new_display),
            user=user,
            old_value=old_severity,
            new_value=new_severity
        )
    
    def log_assignee_change(self, user, old_assignee, new_assignee):
        """Log an assignee change event"""
        old_username = old_assignee.username if old_assignee else _('Unassigned')
        new_username = new_assignee.username if new_assignee else _('Unassigned')
        
        return self.add_timeline_event(
            event_type=AlertEvent.ASSIGNEE_CHANGED,
            title=_('Assignee changed from {old} to {new}').format(old=old_username, new=new_username),
            user=user,
            old_value=str(old_assignee.id) if old_assignee else None,
            new_value=str(new_assignee.id) if new_assignee else None
        )
    
    def log_tlp_change(self, user, old_tlp, new_tlp):
        """Log a TLP change event"""
        old_display = dict(self.TLP_CHOICES).get(old_tlp, old_tlp)
        new_display = dict(self.TLP_CHOICES).get(new_tlp, new_tlp)
        
        return self.add_timeline_event(
            event_type=AlertEvent.TLP_CHANGED,
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
            event_type=AlertEvent.PAP_CHANGED,
            title=_('PAP changed from {old} to {new}').format(old=old_display, new=new_display),
            user=user,
            old_value=old_pap,
            new_value=new_pap
        )
    
    def log_tags_change(self, user, old_tags, new_tags):
        """Log tag changes to timeline"""
        # Create tag names for display
        old_tags_names = ', '.join([tag.name for tag in old_tags]) if old_tags else _('None')
        new_tags_names = ', '.join([tag.name for tag in new_tags]) if new_tags else _('None')
        
        description = _('Changed from: {0} to: {1}').format(old_tags_names, new_tags_names)
        
        return self.add_timeline_event(
            event_type=AlertEvent.TAGS_CHANGED,
            title=_('Tags changed'),
            description=description,
            user=user
        )
    
    def log_observable_added(self, user, observable):
        """Log when an observable is added to the alert"""
        return self.add_timeline_event(
            event_type=AlertEvent.OBSERVABLE_ADDED,
            title=_('Observable added'),
            description=f"{observable.get_type_display()}: {observable.value}",
            user=user,
            metadata={'observable_id': observable.id}
        )
    
    def log_observable_removed(self, user, observable):
        """Log when an observable is removed from the alert"""
        return self.add_timeline_event(
            event_type=AlertEvent.OBSERVABLE_REMOVED,
            title=_('Observable removed'),
            description=f"{observable.get_type_display()}: {observable.value}",
            user=user,
            metadata={'observable_id': observable.id}
        )
    
    def log_escalated_to_case(self, user, case):
        """Log when alert is escalated to a case"""
        return self.add_timeline_event(
            event_type=AlertEvent.ESCALATED,
            title=_('Escalated to case'),
            description=_('Alert was escalated to case: {case}').format(case=case.title),
            user=user,
            metadata={'case_id': case.id}
        )
    
    def log_comment_added(self, user, comment):
        """Log when a comment is added to the alert"""
        return self.add_timeline_event(
            event_type=AlertEvent.COMMENT_ADDED,
            title=_('Comment added by {user}').format(user=user.username),
            description=comment.content[:100] + ('...' if len(comment.content) > 100 else ''),
            user=user,
            metadata={'comment_id': comment.id}
        )
    
    def log_related_alert_added(self, user, related_alert):
        """Log when a related alert is added"""
        return self.add_timeline_event(
            event_type=AlertEvent.RELATED_ALERT_ADDED,
            title=_('Related alert added'),
            description=f"Alert #{related_alert.id}: {related_alert.title}",
            user=user,
            metadata={'related_alert_id': related_alert.id}
        )
    
    def log_related_alert_removed(self, user, related_alert):
        """Log a related alert removed event"""
        return self.add_timeline_event(
            event_type=AlertEvent.RELATED_ALERT_REMOVED,
            title=_('Related alert removed: {alert}').format(alert=related_alert.title),
            user=user,
            metadata={'related_alert_id': related_alert.id}
        )
    
    def log_mitre_attack_added(self, user, item_type, item):
        """Log a MITRE ATT&CK element added event"""
        return self.add_timeline_event(
            event_type=AlertEvent.MITRE_ATTACK_ADDED,
            title=_('MITRE ATT&CK {type} added: {item}').format(
                type=item_type.capitalize(), 
                item=str(item)
            ),
            user=user,
            metadata={
                'mitre_type': item_type,
                'mitre_id': item.pk,
                'mitre_name': item.name
            }
        )
    
    def log_mitre_attack_removed(self, user, item_type, item):
        """Log a MITRE ATT&CK element removed event"""
        return self.add_timeline_event(
            event_type=AlertEvent.MITRE_ATTACK_REMOVED,
            title=_('MITRE ATT&CK {type} removed: {item}').format(
                type=item_type.capitalize(), 
                item=str(item)
            ),
            user=user,
            metadata={
                'mitre_type': item_type,
                'mitre_id': item.pk,
                'mitre_name': item.name
            }
        )
    
    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name = _('Alert')
        verbose_name_plural = _('Alerts')
        ordering = ['-created_at']

class AlertComment(models.Model):
    """Comments on alerts"""
    alert = models.ForeignKey(
        Alert,
        on_delete=models.CASCADE,
        related_name='comments',
    )
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='alert_comments',
    )
    content = models.TextField(_('Content'))
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    
    def __str__(self):
        return f'Comment on {self.alert.title} by {self.user.username}'
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        result = super().save(*args, **kwargs)
        
        # Log timeline event for new comments
        if is_new and hasattr(self, 'alert'):
            self.alert.log_comment_added(self.user, self)
            
        return result
    
    class Meta:
        verbose_name = _('Alert Comment')
        verbose_name_plural = _('Alert Comments')
        ordering = ['-created_at']

class AlertCustomField(models.Model):
    """Custom fields for alerts"""
    TEXT = 'text'
    NUMBER = 'number'
    DATE = 'date'
    BOOLEAN = 'boolean'
    URL = 'url'
    SELECT = 'select'
    
    FIELD_TYPE_CHOICES = [
        (TEXT, _('Text')),
        (NUMBER, _('Number')),
        (DATE, _('Date')),
        (BOOLEAN, _('Boolean')),
        (URL, _('URL')),
        (SELECT, _('Select')),
    ]
    
    name = models.CharField(_('Field Name'), max_length=100)
    label = models.CharField(_('Field Label'), max_length=100)
    field_type = models.CharField(
        _('Field Type'),
        max_length=20,
        choices=FIELD_TYPE_CHOICES,
        default=TEXT,
    )
    required = models.BooleanField(_('Required'), default=False)
    description = models.TextField(_('Description'), blank=True)
    placeholder = models.CharField(_('Placeholder'), max_length=200, blank=True)
    default_value = models.CharField(_('Default Value'), max_length=200, blank=True)
    options = models.JSONField(
        _('Options'),
        blank=True,
        null=True,
        help_text=_('Options for select field type (JSON array)')
    )
    order = models.PositiveIntegerField(_('Display Order'), default=0)
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='alert_custom_fields',
    )
    
    def __str__(self):
        return f"{self.label} ({self.get_field_type_display()})"
    
    class Meta:
        verbose_name = _('Alert Custom Field')
        verbose_name_plural = _('Alert Custom Fields')
        ordering = ['order']
        unique_together = ['name', 'organization']

class AlertCustomValue(models.Model):
    """Values for custom fields on alerts"""
    alert = models.ForeignKey(
        Alert,
        on_delete=models.CASCADE,
        related_name='custom_values',
    )
    field = models.ForeignKey(
        AlertCustomField,
        on_delete=models.CASCADE,
        related_name='values',
    )
    value = models.TextField(_('Value'), blank=True)
    
    def __str__(self):
        return f"{self.field.label}: {self.value}"
    
    class Meta:
        verbose_name = _('Alert Custom Value')
        verbose_name_plural = _('Alert Custom Values')
        unique_together = ['alert', 'field']
