from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


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
    tags = models.ManyToManyField(
        'core.Tag',
        verbose_name=_('Tags'),
        related_name='cases',
        blank=True,
    )
    observables = models.ManyToManyField(
        'core.Observable',
        verbose_name=_('Observables'),
        related_name='cases',
        blank=True,
    )
    # MITRE ATT&CK relations
    mitre_tactics = models.ManyToManyField(
        'core.MitreTactic',
        verbose_name=_('MITRE Tactics'),
        related_name='cases',
        blank=True,
    )
    mitre_techniques = models.ManyToManyField(
        'core.MitreTechnique',
        verbose_name=_('MITRE Techniques'),
        related_name='cases',
        blank=True,
    )
    mitre_subtechniques = models.ManyToManyField(
        'core.MitreSubTechnique',
        verbose_name=_('MITRE Sub-techniques'),
        related_name='cases',
        blank=True,
    )
    # Grupos MITRE ATT&CK para suportar múltiplos vínculos MITRE em um caso
    mitre_attack_groups = models.ManyToManyField(
        'core.MitreAttackGroup',
        verbose_name=_('MITRE ATT&CK Groups'),
        related_name='cases',
        blank=True,
        help_text=_('Grupos de elementos MITRE ATT&CK (táticas, técnicas, subtécnicas) relacionados'),
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
        old_display = old_date.strftime('%Y-%m-%d') if old_date else _('None')
        new_display = new_date.strftime('%Y-%m-%d') if new_date else _('None')
        
        return self.add_timeline_event(
            event_type=CaseEvent.DUE_DATE_CHANGED,
            title=_('Due date changed from {old} to {new}').format(old=old_display, new=new_display),
            user=user,
            old_value=str(old_date) if old_date else None,
            new_value=str(new_date) if new_date else None
        )
    
    def log_comment_added(self, user, comment):
        """Log a comment added event"""
        return self.add_timeline_event(
            event_type=CaseEvent.COMMENT_ADDED,
            title=_('Comment added'),
            description=comment.content[:100] + ('...' if len(comment.content) > 100 else ''),
            user=user,
            metadata={'comment_id': comment.id}
        )
    
    def log_attachment_added(self, user, attachment):
        """Log an attachment added event"""
        return self.add_timeline_event(
            event_type=CaseEvent.ATTACHMENT_ADDED,
            title=_('Attachment added: {filename}').format(filename=attachment.filename),
            user=user,
            metadata={'attachment_id': attachment.id}
        )
    
    def log_alert_linked(self, user, alert):
        """Log an alert linked event"""
        return self.add_timeline_event(
            event_type=CaseEvent.ALERT_LINKED,
            title=_('Alert linked: {title}').format(title=alert.title),
            user=user,
            metadata={'alert_id': alert.id}
        )
    
    def log_alert_unlinked(self, user, alert):
        """Log an alert unlinked event"""
        return self.add_timeline_event(
            event_type=CaseEvent.ALERT_UNLINKED,
            title=_('Alert unlinked: {title}').format(title=alert.title),
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
    
    def log_tags_change(self, user, old_tags, new_tags):
        """Log a tags change event"""
        if hasattr(old_tags, 'all'):
            old_tags = list(old_tags.all())
        if hasattr(new_tags, 'all'):
            new_tags = list(new_tags.all())
        
        old_names = [tag.name for tag in old_tags] if isinstance(old_tags, (list, set)) else []
        new_names = [tag.name for tag in new_tags] if isinstance(new_tags, (list, set)) else new_tags
        
        added = [name for name in new_names if name not in old_names]
        removed = [name for name in old_names if name not in new_names]
        
        description = ""
        if added:
            description += _('Added: {}').format(', '.join(added))
        if removed:
            description += _(' Removed: {}').format(', '.join(removed)) if description else _('Removed: {}').format(', '.join(removed))
        
        return self.add_timeline_event(
            event_type=CaseEvent.TAGS_CHANGED,
            title=_('Tags updated'),
            description=description,
            user=user
        )
    
    def log_observable_added(self, user, observable):
        """Log an observable added event"""
        return self.add_timeline_event(
            event_type=CaseEvent.OBSERVABLE_ADDED,
            title=_('Observable added: {value}').format(value=observable.value),
            description=_('Type: {type}').format(type=observable.get_type_display()),
            user=user,
            metadata={'observable_id': observable.id}
        )
    
    def log_observable_removed(self, user, observable):
        """Log an observable removed event"""
        return self.add_timeline_event(
            event_type=CaseEvent.OBSERVABLE_REMOVED,
            title=_('Observable removed: {value}').format(value=observable.value),
            description=_('Type: {type}').format(type=observable.get_type_display()),
            user=user,
            metadata={'observable_id': observable.id}
        )
    
    def log_task_added(self, user, task):
        """Log a task added event"""
        return self.add_timeline_event(
            event_type=CaseEvent.TASK_ADDED,
            title=_('Task added: {title}').format(title=task.title),
            user=user,
            metadata={'task_id': task.id}
        )
    
    def log_task_updated(self, user, task, old_data=None):
        """Log a task updated event"""
        changes = []
        
        if old_data:
            if old_data.get('title') != task.title:
                changes.append(_('Title changed'))
            
            if old_data.get('description') != task.description:
                changes.append(_('Description changed'))
            
            if old_data.get('assigned_to_id') != task.assigned_to_id:
                old_assignee = 'Unassigned'
                new_assignee = 'Unassigned'
                
                if old_data.get('assigned_to_id'):
                    from accounts.models import User
                    try:
                        old_user = User.objects.get(pk=old_data.get('assigned_to_id'))
                        old_assignee = old_user.username
                    except User.DoesNotExist:
                        pass
                
                if task.assigned_to:
                    new_assignee = task.assigned_to.username
                
                changes.append(_('Assignee changed from {old} to {new}').format(old=old_assignee, new=new_assignee))
            
            if old_data.get('due_date') != task.due_date:
                old_date = old_data.get('due_date')
                new_date = task.due_date
                
                old_display = old_date.strftime('%Y-%m-%d') if old_date else 'None'
                new_display = new_date.strftime('%Y-%m-%d') if new_date else 'None'
                
                changes.append(_('Due date changed from {old} to {new}').format(old=old_display, new=new_display))
            
            if old_data.get('priority') != task.priority:
                changes.append(_('Priority changed from {old} to {new}').format(
                    old=dict(Task.PRIORITY_CHOICES).get(old_data.get('priority'), old_data.get('priority')),
                    new=dict(Task.PRIORITY_CHOICES).get(task.priority, task.priority)
                ))
        
        description = '\n'.join(changes) if changes else _('Task details updated')
        
        return self.add_timeline_event(
            event_type=CaseEvent.TASK_UPDATED,
            title=_('Task updated: {title}').format(title=task.title),
            description=description,
            user=user,
            metadata={'task_id': task.id}
        )
    
    def log_task_completed(self, user, task):
        """Log a task completed event"""
        return self.add_timeline_event(
            event_type=CaseEvent.TASK_COMPLETED,
            title=_('Task completed: {title}').format(title=task.title),
            user=user,
            metadata={'task_id': task.id}
        )
    
    def log_mitre_attack_added(self, user, item_type, item):
        """Log MITRE ATT&CK item added event"""
        if item_type == 'tactic':
            title = _('MITRE Tactic added: {name}').format(name=item.name)
            description = _('ID: {id}').format(id=item.tactic_id)
        elif item_type == 'technique':
            title = _('MITRE Technique added: {name}').format(name=item.name)
            description = _('ID: {id}').format(id=item.technique_id)
        elif item_type == 'subtechnique':
            title = _('MITRE Sub-technique added: {name}').format(name=item.name)
            description = _('ID: {id}').format(id=item.sub_technique_id)
        elif item_type == 'attack_group':
            title = _('MITRE ATT&CK Group added: {name}').format(name=item.name)
            description = _('ID: {id}').format(id=item.id)
        else:
            title = _('MITRE ATT&CK item added')
            description = ''
        
        return self.add_timeline_event(
            event_type=CaseEvent.MITRE_ATTACK_ADDED,
            title=title,
            description=description,
            user=user,
            metadata={'item_type': item_type, 'item_id': item.id}
        )
    
    def log_mitre_attack_removed(self, user, item_type, item):
        """Log MITRE ATT&CK item removed event"""
        if item_type == 'tactic':
            title = _('MITRE Tactic removed: {name}').format(name=item.name)
            description = _('ID: {id}').format(id=item.tactic_id)
        elif item_type == 'technique':
            title = _('MITRE Technique removed: {name}').format(name=item.name)
            description = _('ID: {id}').format(id=item.technique_id)
        elif item_type == 'subtechnique':
            title = _('MITRE Sub-technique removed: {name}').format(name=item.name)
            description = _('ID: {id}').format(id=item.sub_technique_id)
        elif item_type == 'attack_group':
            title = _('MITRE ATT&CK Group removed: {name}').format(name=item.name)
            description = _('ID: {id}').format(id=item.id)
        else:
            title = _('MITRE ATT&CK item removed')
            description = ''
        
        return self.add_timeline_event(
            event_type=CaseEvent.MITRE_ATTACK_REMOVED,
            title=title,
            description=description,
            user=user,
            metadata={'item_type': item_type, 'item_id': item.id}
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
        return f"Comment on {self.case.title} by {self.user.username}"
    
    def save(self, *args, **kwargs):
        # Register comment in timeline if it's a new comment
        is_new = self.pk is None
        result = super().save(*args, **kwargs)
        
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
        # Register attachment in timeline if it's a new attachment
        is_new = self.pk is None
        result = super().save(*args, **kwargs)
        
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
    TAGS_CHANGED = 'tags_changed'
    OBSERVABLE_ADDED = 'observable_added'
    OBSERVABLE_REMOVED = 'observable_removed'
    TASK_ADDED = 'task_added'
    TASK_UPDATED = 'task_updated'
    TASK_COMPLETED = 'task_completed'
    MITRE_ATTACK_ADDED = 'mitre_attack_added'
    MITRE_ATTACK_REMOVED = 'mitre_attack_removed'
    THREAT_INTEL_ADDED = 'threat_intel_added'
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
        (TAGS_CHANGED, _('Tags Changed')),
        (OBSERVABLE_ADDED, _('Observable Added')),
        (OBSERVABLE_REMOVED, _('Observable Removed')),
        (TASK_ADDED, _('Task Added')),
        (TASK_UPDATED, _('Task Updated')),
        (TASK_COMPLETED, _('Task Completed')),
        (MITRE_ATTACK_ADDED, _('MITRE ATT&CK Added')),
        (MITRE_ATTACK_REMOVED, _('MITRE ATT&CK Removed')),
        (THREAT_INTEL_ADDED, _('Threat Intelligence Added')),
        (CUSTOM, _('Custom Event')),
    ]
    
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name='timeline_events',
    )
    event_type = models.CharField(
        _('Event Type'),
        max_length=25,
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
        """Get Bootstrap icon class for this event type"""
        icon_mapping = {
            self.CREATED: 'fa-plus-circle text-success',
            self.STATUS_CHANGED: 'fa-exchange-alt text-info',
            self.PRIORITY_CHANGED: 'fa-flag text-warning',
            self.ASSIGNEE_CHANGED: 'fa-user-friends text-info',
            self.DUE_DATE_CHANGED: 'fa-calendar-alt text-info',
            self.COMMENT_ADDED: 'fa-comment text-info',
            self.ATTACHMENT_ADDED: 'fa-paperclip text-info',
            self.ALERT_LINKED: 'fa-bell text-danger',
            self.ALERT_UNLINKED: 'fa-bell-slash text-warning',
            self.TLP_CHANGED: 'fa-traffic-light text-info',
            self.PAP_CHANGED: 'fa-shield-alt text-info',
            self.TAGS_CHANGED: 'fa-tags text-info',
            self.OBSERVABLE_ADDED: 'fa-search-plus text-success',
            self.OBSERVABLE_REMOVED: 'fa-search-minus text-danger',
            self.TASK_ADDED: 'fa-tasks text-info',
            self.TASK_UPDATED: 'fa-edit text-warning',
            self.TASK_COMPLETED: 'fa-check-circle text-success',
            self.MITRE_ATTACK_ADDED: 'fa-shield-alt text-warning',
            self.MITRE_ATTACK_REMOVED: 'fa-shield-alt text-danger',
            self.THREAT_INTEL_ADDED: 'fa-database text-info',
            self.CUSTOM: 'fa-star text-warning',
        }
        return icon_mapping.get(self.event_type, 'fa-circle')
    
    class Meta:
        verbose_name = _('Case Event')
        verbose_name_plural = _('Case Events')
        ordering = ['-created_at']


class Task(models.Model):
    """Tasks associated with cases"""
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    
    PRIORITY_CHOICES = [
        (LOW, _('Low')),
        (MEDIUM, _('Medium')),
        (HIGH, _('High')),
    ]
    
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name='tasks',
    )
    title = models.CharField(_('Title'), max_length=255)
    description = models.TextField(_('Description'), blank=True)
    assigned_to = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        related_name='assigned_tasks',
        null=True,
        blank=True,
    )
    due_date = models.DateField(_('Due Date'), null=True, blank=True)
    priority = models.CharField(
        _('Priority'),
        max_length=10,
        choices=PRIORITY_CHOICES,
        default=MEDIUM,
    )
    is_completed = models.BooleanField(_('Completed'), default=False)
    completed_at = models.DateTimeField(_('Completed at'), null=True, blank=True)
    completed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        related_name='completed_tasks',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated at'), auto_now=True)
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        # Check if this is a new task
        is_new = self.pk is None
        
        # Store old data for tracking changes if it's an existing task
        if not is_new:
            old_data = {
                'title': Task.objects.get(pk=self.pk).title,
                'description': Task.objects.get(pk=self.pk).description,
                'assigned_to_id': Task.objects.get(pk=self.pk).assigned_to_id,
                'due_date': Task.objects.get(pk=self.pk).due_date,
                'priority': Task.objects.get(pk=self.pk).priority,
                'is_completed': Task.objects.get(pk=self.pk).is_completed,
            }
        
        # Check if task is being marked as completed
        was_completed = False
        if not is_new and not Task.objects.get(pk=self.pk).is_completed and self.is_completed:
            was_completed = True
            self.completed_at = timezone.now()
        
        # Save the task
        result = super().save(*args, **kwargs)
        
        # Add timeline events if there's a case
        if hasattr(self, 'case'):
            current_user = getattr(self, '_current_user', None)
            
            if is_new and current_user:
                # Log task creation
                self.case.log_task_added(current_user, self)
            elif not is_new and current_user:
                # Log task update
                if was_completed:
                    self.case.log_task_completed(current_user, self)
                else:
                    self.case.log_task_updated(current_user, self, old_data)
        
        return result
    
    # Method to set current user for timeline events
    def set_current_user(self, user):
        self._current_user = user
        return self
    
    class Meta:
        verbose_name = _('Task')
        verbose_name_plural = _('Tasks')
        ordering = ['is_completed', 'priority', 'due_date', '-created_at']


class ThreatCategory(models.Model):
    """Categories of threats for automated task generation"""
    PHISHING = 'phishing'
    MALWARE = 'malware'
    RANSOMWARE = 'ransomware'
    DATA_BREACH = 'data_breach'
    INSIDER_THREAT = 'insider_threat'
    DDoS = 'ddos'
    UNAUTHORIZED_ACCESS = 'unauthorized_access'
    SOCIAL_ENGINEERING = 'social_engineering'
    SUPPLY_CHAIN = 'supply_chain'
    OTHER = 'other'
    
    CATEGORY_CHOICES = [
        (PHISHING, _('Phishing')),
        (MALWARE, _('Malware')),
        (RANSOMWARE, _('Ransomware')),
        (DATA_BREACH, _('Data Breach')),
        (INSIDER_THREAT, _('Insider Threat')),
        (DDoS, _('DDoS')),
        (UNAUTHORIZED_ACCESS, _('Unauthorized Access')),
        (SOCIAL_ENGINEERING, _('Social Engineering')),
        (SUPPLY_CHAIN, _('Supply Chain')),
        (OTHER, _('Other')),
    ]
    
    name = models.CharField(
        _('Name'),
        max_length=50,
        choices=CATEGORY_CHOICES,
        unique=True
    )
    description = models.TextField(_('Description'), blank=True)
    icon_class = models.CharField(_('Icon Class'), max_length=50, blank=True)
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated at'), auto_now=True)
    
    def __str__(self):
        return self.get_name_display()
    
    class Meta:
        verbose_name = _('Threat Category')
        verbose_name_plural = _('Threat Categories')
        ordering = ['name']


class TaskTemplate(models.Model):
    """Templates for tasks to be created automatically based on threat category"""
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    
    PRIORITY_CHOICES = [
        (LOW, _('Low')),
        (MEDIUM, _('Medium')),
        (HIGH, _('High')),
    ]
    
    title = models.CharField(_('Title'), max_length=255)
    description = models.TextField(_('Description'), blank=True)
    priority = models.CharField(
        _('Priority'),
        max_length=10,
        choices=PRIORITY_CHOICES,
        default=MEDIUM,
    )
    threat_category = models.ForeignKey(
        ThreatCategory, 
        on_delete=models.CASCADE,
        related_name='task_templates',
        verbose_name=_('Threat Category')
    )
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='task_templates',
    )
    is_active = models.BooleanField(_('Active'), default=True)
    order = models.PositiveIntegerField(_('Order'), default=0)
    due_days = models.PositiveIntegerField(_('Due Days'), default=7, help_text=_('Number of days after case creation to set as due date'))
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated at'), auto_now=True)
    
    def __str__(self):
        return f"{self.title} ({self.threat_category})"
    
    class Meta:
        verbose_name = _('Task Template')
        verbose_name_plural = _('Task Templates')
        ordering = ['threat_category', 'order', 'title']
