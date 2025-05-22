from django.db.models.signals import post_save, pre_save, m2m_changed
from django.dispatch import receiver
from django.utils import timezone
from cases.models import Case, CaseEvent, Task
from alerts.models import Alert, AlertEvent
from core.models import Observable
from .services import NotificationService


# ===== Case Signal Handlers =====

@receiver(post_save, sender=Case)
def case_post_save(sender, instance, created, **kwargs):
    """Handle case creation and updates"""
    if created:
        # Case creation
        data = {
            'case_id': instance.id,
            'title': instance.title,
            'description': instance.description,
            'priority': instance.priority,
            'status': instance.status,
            'tlp': instance.tlp,
            'pap': instance.pap,
            'created_at': timezone.now().isoformat(),
            'event_type': 'created',
            'source_type': 'case',
            'source_id': instance.id
        }
        
        NotificationService.process_event(
            event_type='created',
            source_type='case',
            source_id=str(instance.id),
            data=data,
            organization=instance.organization
        )


@receiver(post_save, sender=CaseEvent)
def case_event_post_save(sender, instance, created, **kwargs):
    """Handle case events for notifications"""
    if created and instance.event_type in [
        CaseEvent.STATUS_CHANGED,
        CaseEvent.PRIORITY_CHANGED,
        CaseEvent.ASSIGNEE_CHANGED,
        CaseEvent.COMMENT_ADDED,
        CaseEvent.ATTACHMENT_ADDED
    ]:
        # Map CaseEvent types to notification event types
        event_type_map = {
            CaseEvent.STATUS_CHANGED: 'status_changed',
            CaseEvent.PRIORITY_CHANGED: 'case_priority_changed',
            CaseEvent.ASSIGNEE_CHANGED: 'assigned',
            CaseEvent.COMMENT_ADDED: 'case_comment_added',
            CaseEvent.ATTACHMENT_ADDED: 'case_attachment_added'
        }
        
        notification_event_type = event_type_map.get(instance.event_type)
        if not notification_event_type:
            return
        
        # Basic event data
        data = {
            'case_id': instance.case.id,
            'case_title': instance.case.title,
            'event_id': instance.id,
            'event_title': instance.title,
            'event_description': instance.description,
            'user': instance.user.username if instance.user else None,
            'created_at': timezone.now().isoformat(),
            'event_type': notification_event_type,
            'source_type': 'case',
            'source_id': instance.case.id
        }
        
        # Add old/new values if available
        if instance.old_value:
            data['old_value'] = instance.old_value
        if instance.new_value:
            data['new_value'] = instance.new_value
        
        # Add metadata if available
        if instance.metadata:
            data['metadata'] = instance.metadata
        
        NotificationService.process_event(
            event_type=notification_event_type,
            source_type='case',
            source_id=str(instance.case.id),
            data=data,
            organization=instance.case.organization
        )


@receiver(post_save, sender=Task)
def task_post_save(sender, instance, created, **kwargs):
    """Handle task creation and status changes"""
    # Get previous state to detect completion
    if not created and instance.is_completed and not instance._old_is_completed:
        # Task completed
        data = {
            'task_id': instance.id,
            'task_title': instance.title,
            'case_id': instance.case.id,
            'case_title': instance.case.title,
            'completed_by': instance.completed_by.username if instance.completed_by else None,
            'completed_at': instance.completed_at.isoformat() if instance.completed_at else None,
            'created_at': timezone.now().isoformat(),
            'event_type': 'task_completed',
            'source_type': 'task',
            'source_id': instance.id
        }
        
        NotificationService.process_event(
            event_type='task_completed',
            source_type='task',
            source_id=str(instance.id),
            data=data,
            organization=instance.case.organization
        )
    
    # Check for overdue tasks daily (this should be handled by a scheduled task)
    # This is just a placeholder as a real implementation would use a task scheduler


# ===== Alert Signal Handlers =====

@receiver(post_save, sender=Alert)
def alert_post_save(sender, instance, created, **kwargs):
    """Handle alert creation and updates"""
    if created:
        # Alert creation
        data = {
            'alert_id': instance.id,
            'title': instance.title,
            'description': instance.description,
            'severity': instance.severity,
            'status': instance.status,
            'tlp': instance.tlp,
            'pap': instance.pap,
            'created_at': timezone.now().isoformat(),
            'event_type': 'created',
            'source_type': 'alert',
            'source_id': instance.id
        }
        
        NotificationService.process_event(
            event_type='created',
            source_type='alert',
            source_id=str(instance.id),
            data=data,
            organization=instance.organization
        )


@receiver(post_save, sender=AlertEvent)
def alert_event_post_save(sender, instance, created, **kwargs):
    """Handle alert events for notifications"""
    if created and instance.event_type in [
        AlertEvent.STATUS_CHANGED,
        AlertEvent.SEVERITY_CHANGED,
        AlertEvent.ASSIGNEE_CHANGED,
        AlertEvent.ESCALATED
    ]:
        # Map AlertEvent types to notification event types
        event_type_map = {
            AlertEvent.STATUS_CHANGED: 'status_changed',
            AlertEvent.SEVERITY_CHANGED: 'alert_severity_changed',
            AlertEvent.ASSIGNEE_CHANGED: 'assigned',
            AlertEvent.ESCALATED: 'alert_escalated'
        }
        
        notification_event_type = event_type_map.get(instance.event_type)
        if not notification_event_type:
            return
        
        # Basic event data
        data = {
            'alert_id': instance.alert.id,
            'alert_title': instance.alert.title,
            'event_id': instance.id,
            'event_title': instance.title,
            'event_description': instance.description,
            'user': instance.user.username if instance.user else None,
            'created_at': timezone.now().isoformat(),
            'event_type': notification_event_type,
            'source_type': 'alert',
            'source_id': instance.alert.id
        }
        
        # Add old/new values if available
        if instance.old_value:
            data['old_value'] = instance.old_value
        if instance.new_value:
            data['new_value'] = instance.new_value
        
        # Add metadata if available
        if instance.metadata:
            data['metadata'] = instance.metadata
        
        NotificationService.process_event(
            event_type=notification_event_type,
            source_type='alert',
            source_id=str(instance.alert.id),
            data=data,
            organization=instance.alert.organization
        )


# ===== Observable Signal Handlers =====

@receiver(post_save, sender=Observable)
def observable_post_save(sender, instance, created, **kwargs):
    """Handle malicious observable creation"""
    # Only trigger notifications for malicious observables
    if instance.is_malicious:
        data = {
            'observable_id': instance.id,
            'value': instance.value,
            'type': instance.type,
            'is_malicious': instance.is_malicious,
            'confidence': instance.confidence,
            'pap': instance.pap,
            'created_at': timezone.now().isoformat(),
            'event_type': 'observable_malicious_added',
            'source_type': 'observable',
            'source_id': instance.id
        }
        
        NotificationService.process_event(
            event_type='observable_malicious_added',
            source_type='observable',
            source_id=str(instance.id),
            data=data,
            organization=instance.organization
        )


# Add a hook for Task model to track old state
def _task_pre_save(sender, instance, **kwargs):
    """Save old is_completed value for detecting status changes"""
    if instance.pk:
        try:
            old_instance = Task.objects.get(pk=instance.pk)
            instance._old_is_completed = old_instance.is_completed
        except Task.DoesNotExist:
            instance._old_is_completed = False
    else:
        instance._old_is_completed = False

# Connect pre_save signal for Task
pre_save.connect(_task_pre_save, sender=Task) 