from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.auth.signals import user_login_failed
from django.db.backends.signals import connection_created
from .services import NotificationService


def send_system_notification(event_type, data, organization=None):
    """
    Helper function to send system notifications
    
    Args:
        event_type (str): System event type
        data (dict): Event data
        organization: Optional organization (can be None for global events)
    """
    # Add common fields
    data.update({
        'event_type': event_type,
        'source_type': 'system',
        'timestamp': timezone.now().isoformat(),
    })
    
    # If we have an organization, process through that org
    if organization:
        NotificationService.process_event(
            event_type=event_type,
            source_type='system',
            source_id='system',
            data=data,
            organization=organization
        )
    else:
        # If no organization, we need to iterate through all organizations
        # For system-wide events like backups or errors
        from organizations.models import Organization
        
        # Only process for active organizations
        for org in Organization.objects.filter(is_active=True):
            NotificationService.process_event(
                event_type=event_type,
                source_type='system',
                source_id='system',
                data=data,
                organization=org
            )


@receiver(user_login_failed)
def handle_user_login_failed(sender, credentials, **kwargs):
    """Handle user login failed events"""
    username = credentials.get('username', 'unknown')
    
    data = {
        'username': username,
        'ip_address': '',  # This would need to be passed from the view
        'timestamp': timezone.now().isoformat(),
        'system_event': 'user_login_failed'
    }
    
    # This is a global event, so we pass None as organization
    # It will be sent to all active organizations
    send_system_notification('system_user_login_failed', data)


def handle_database_backup_completed(backup_file, duration, status, organization=None):
    """
    Handle database backup completed events
    
    This should be called from the backup task or script
    """
    data = {
        'backup_file': backup_file,
        'duration_seconds': duration,
        'status': status,
        'timestamp': timezone.now().isoformat(),
        'system_event': 'database_backup'
    }
    
    send_system_notification('system_database_backup', data, organization)


def handle_system_error(error_message, error_type, component, severity='error', organization=None):
    """
    Handle system error events
    
    This should be called from exception handling code
    """
    data = {
        'error_message': error_message,
        'error_type': error_type,
        'component': component,
        'severity': severity,
        'timestamp': timezone.now().isoformat(),
        'system_event': 'system_error'
    }
    
    send_system_notification('system_error', data, organization) 