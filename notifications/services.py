from django.conf import settings
from django.core.mail import send_mail
from django.template import Template, Context
from django.utils import timezone
import requests
import json
import logging
import traceback
from .models import NotificationLog, NotificationRule, NotificationDestination, NotificationEvent
from .tasks import (
    send_email_notification, 
    send_webhook_notification, 
    send_slack_notification, 
    send_mattermost_notification, 
    send_custom_http_notification,
    process_notification_event
)

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for handling notification dispatch"""
    
    @classmethod
    def process_event(cls, event_type, source_type, source_id, data, organization):
        """
        Process a notification event
        
        Args:
            event_type (str): The type of event (created, updated, etc.)
            source_type (str): The source of the event (case, alert, etc.)
            source_id (str): The ID of the source
            data (dict): Data related to the event
            organization: The organization the event belongs to
        """
        # Create notification event record
        event = NotificationEvent.objects.create(
            source_id=source_id,
            source_type=source_type,
            event_type=event_type,
            event_data=data,
            organization=organization,
            processed=False
        )
        
        # Process event asynchronously
        process_notification_event.delay(event.id)
        
        return event
    
    @classmethod
    def _find_matching_rules(cls, event):
        """Find rules that match this event"""
        # Basic matching: source type and event type
        rules = NotificationRule.objects.filter(
            source=event.source_type,
            event_type=event.event_type,
            is_active=True,
            organization=event.organization
        )
        
        matching_rules = []
        
        # Check additional conditions
        for rule in rules:
            if cls._check_conditions(rule, event.event_data):
                matching_rules.append(rule)
        
        return matching_rules
    
    @classmethod
    def _check_conditions(cls, rule, data):
        """Check if the event data matches the rule conditions"""
        # No conditions means always match
        if not rule.conditions:
            return True
        
        conditions = rule.conditions
        
        # Simple field value matching
        for field, expected_value in conditions.items():
            # Handle nested fields using dot notation
            if '.' in field:
                parts = field.split('.')
                value = data
                for part in parts:
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        return False
            else:
                if field not in data:
                    return False
                value = data[field]
            
            # Check if field value matches expected value
            if isinstance(expected_value, list):
                # List of possible values
                if value not in expected_value:
                    return False
            else:
                # Single value
                if value != expected_value:
                    return False
        
        return True
    
    @classmethod
    def _format_templates(cls, rule, data):
        """Format template strings with data"""
        context = Context(data)
        
        # Default templates if not specified
        subject_template = rule.template_subject or "Notification from SentinelIQ"
        body_template = rule.template_body or "Event: {{ event_type }} for {{ source_type }} {{ source_id }}"
        
        # Create Django templates
        subject_tpl = Template(subject_template)
        body_tpl = Template(body_template)
        
        # Render templates
        subject = subject_tpl.render(context)
        body = body_tpl.render(context)
        
        return subject, body
    
    @classmethod
    def send_notification(cls, notification_log):
        """Send a notification based on its destination type"""
        destination = notification_log.destination
        
        # Queue the appropriate Celery task based on destination type
        if destination.type == NotificationDestination.EMAIL:
            send_email_notification.delay(notification_log.id)
        elif destination.type == NotificationDestination.WEBHOOK:
            send_webhook_notification.delay(notification_log.id)
        elif destination.type == NotificationDestination.SLACK:
            send_slack_notification.delay(notification_log.id)
        elif destination.type == NotificationDestination.MATTERMOST:
            send_mattermost_notification.delay(notification_log.id)
        elif destination.type == NotificationDestination.CUSTOM_HTTP:
            send_custom_http_notification.delay(notification_log.id)
        else:
            raise ValueError(f"Unsupported destination type: {destination.type}")
        
        return notification_log
    
    @classmethod
    def _send_email(cls, notification_log):
        """Send notification via email"""
        destination = notification_log.destination
        config = destination.config
        
        # Get recipients from config
        recipients = config.get('recipients', [])
        if not recipients:
            notification_log.mark_as_failed("No recipients specified in destination config")
            return
        
        # Get sender email
        from_email = config.get('from_email', settings.DEFAULT_FROM_EMAIL)
        
        try:
            # Send email
            send_mail(
                notification_log.subject,
                notification_log.body,
                from_email,
                recipients,
                fail_silently=False,
                html_message=notification_log.body if config.get('use_html', False) else None
            )
            notification_log.mark_as_sent()
        except Exception as e:
            error_msg = f"Failed to send email: {str(e)}\n{traceback.format_exc()}"
            notification_log.mark_as_failed(error_msg)
            logger.error(error_msg)
    
    @classmethod
    def _send_webhook(cls, notification_log):
        """Send notification via webhook"""
        destination = notification_log.destination
        config = destination.config
        
        # Get webhook URL
        webhook_url = config.get('url')
        if not webhook_url:
            notification_log.mark_as_failed("No URL specified in destination config")
            return
        
        # Prepare headers and payload
        headers = config.get('headers', {})
        headers.setdefault('Content-Type', 'application/json')
        
        payload = {
            'subject': notification_log.subject,
            'body': notification_log.body,
            'event_data': notification_log.event_data,
            'tracking_id': str(notification_log.tracking_id),
            'timestamp': timezone.now().isoformat()
        }
        
        try:
            # Send webhook
            response = requests.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=config.get('timeout', 10)
            )
            
            if response.status_code >= 200 and response.status_code < 300:
                notification_log.mark_as_sent()
            else:
                error_msg = f"Webhook returned non-success status code: {response.status_code}, response: {response.text}"
                notification_log.mark_as_failed(error_msg)
                logger.error(error_msg)
        except Exception as e:
            error_msg = f"Failed to send webhook: {str(e)}\n{traceback.format_exc()}"
            notification_log.mark_as_failed(error_msg)
            logger.error(error_msg)
    
    @classmethod
    def _send_slack(cls, notification_log):
        """Send notification to Slack"""
        destination = notification_log.destination
        config = destination.config
        
        # Get webhook URL
        webhook_url = config.get('webhook_url')
        if not webhook_url:
            notification_log.mark_as_failed("No webhook URL specified in destination config")
            return
        
        # Prepare payload
        payload = {
            'text': notification_log.subject,
            'blocks': [
                {
                    'type': 'header',
                    'text': {
                        'type': 'plain_text',
                        'text': notification_log.subject
                    }
                },
                {
                    'type': 'section',
                    'text': {
                        'type': 'mrkdwn',
                        'text': notification_log.body
                    }
                }
            ]
        }
        
        # Add custom fields if specified
        if config.get('include_fields', False) and notification_log.event_data:
            fields = []
            for key, value in notification_log.event_data.items():
                if isinstance(value, (dict, list)):
                    # Skip complex values
                    continue
                fields.append({
                    'type': 'mrkdwn',
                    'text': f"*{key}*: {value}"
                })
            
            if fields:
                payload['blocks'].append({
                    'type': 'section',
                    'fields': fields[:10]  # Limit to 10 fields
                })
        
        try:
            # Send to Slack
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=config.get('timeout', 10)
            )
            
            if response.status_code == 200:
                notification_log.mark_as_sent()
            else:
                error_msg = f"Slack webhook returned non-success status code: {response.status_code}, response: {response.text}"
                notification_log.mark_as_failed(error_msg)
                logger.error(error_msg)
        except Exception as e:
            error_msg = f"Failed to send to Slack: {str(e)}\n{traceback.format_exc()}"
            notification_log.mark_as_failed(error_msg)
            logger.error(error_msg)
    
    @classmethod
    def _send_mattermost(cls, notification_log):
        """Send notification to Mattermost"""
        destination = notification_log.destination
        config = destination.config
        
        # Get webhook URL
        webhook_url = config.get('webhook_url')
        if not webhook_url:
            notification_log.mark_as_failed("No webhook URL specified in destination config")
            return
        
        # Prepare payload
        payload = {
            'text': notification_log.subject,
            'title': notification_log.subject,
            'username': config.get('username', 'SentinelIQ Bot'),
            'icon_url': config.get('icon_url', '')
        }
        
        if config.get('use_attachment', True):
            payload['attachments'] = [{
                'pretext': notification_log.subject,
                'text': notification_log.body,
                'color': config.get('color', '#2377E5')  # Default blue color
            }]
        else:
            payload['text'] = f"## {notification_log.subject}\n\n{notification_log.body}"
        
        try:
            # Send to Mattermost
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=config.get('timeout', 10)
            )
            
            if response.status_code >= 200 and response.status_code < 300:
                notification_log.mark_as_sent()
            else:
                error_msg = f"Mattermost webhook returned non-success status code: {response.status_code}, response: {response.text}"
                notification_log.mark_as_failed(error_msg)
                logger.error(error_msg)
        except Exception as e:
            error_msg = f"Failed to send to Mattermost: {str(e)}\n{traceback.format_exc()}"
            notification_log.mark_as_failed(error_msg)
            logger.error(error_msg)
    
    @classmethod
    def _send_custom_http(cls, notification_log):
        """Send notification via custom HTTP request"""
        destination = notification_log.destination
        config = destination.config
        
        # Get URL and method
        url = config.get('url')
        if not url:
            notification_log.mark_as_failed("No URL specified in destination config")
            return
        
        method = config.get('method', 'POST').upper()
        
        # Prepare headers and payload
        headers = config.get('headers', {})
        content_type = headers.get('Content-Type', 'application/json')
        
        # Base payload
        payload = {
            'subject': notification_log.subject,
            'body': notification_log.body,
            'event_data': notification_log.event_data,
            'tracking_id': str(notification_log.tracking_id),
            'timestamp': timezone.now().isoformat()
        }
        
        # Apply custom template if provided
        template = config.get('payload_template')
        if template:
            try:
                context = Context(payload)
                tpl = Template(template)
                payload = json.loads(tpl.render(context))
            except Exception as e:
                error_msg = f"Failed to apply custom payload template: {str(e)}"
                notification_log.mark_as_failed(error_msg)
                logger.error(error_msg)
                return
        
        # Prepare request data
        request_kwargs = {
            'url': url,
            'headers': headers,
            'timeout': config.get('timeout', 10)
        }
        
        if method in ('POST', 'PUT', 'PATCH'):
            if 'application/json' in content_type:
                request_kwargs['json'] = payload
            else:
                request_kwargs['data'] = payload
        else:
            request_kwargs['params'] = payload
        
        try:
            # Send request
            response = requests.request(method, **request_kwargs)
            
            if response.status_code >= 200 and response.status_code < 300:
                notification_log.mark_as_sent()
            else:
                error_msg = f"HTTP request returned non-success status code: {response.status_code}, response: {response.text}"
                notification_log.mark_as_failed(error_msg)
                logger.error(error_msg)
        except Exception as e:
            error_msg = f"Failed to send HTTP request: {str(e)}\n{traceback.format_exc()}"
            notification_log.mark_as_failed(error_msg)
            logger.error(error_msg) 