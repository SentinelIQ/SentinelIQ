from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from organizations.models import Organization
from notifications.services import NotificationService
import json


class Command(BaseCommand):
    help = 'Send a test notification to test the notification framework'
    
    def add_arguments(self, parser):
        parser.add_argument('--org', type=int, help='Organization ID')
        parser.add_argument('--source', type=str, choices=['case', 'alert', 'task', 'observable', 'system'],
                            default='system', help='Source type')
        parser.add_argument('--event', type=str, default='test_event', help='Event type')
        parser.add_argument('--subject', type=str, default='Test Notification', help='Notification subject')
        parser.add_argument('--message', type=str, default='This is a test notification from the command line.',
                            help='Notification message')
    
    def handle(self, *args, **options):
        # Get organization
        org_id = options.get('org')
        if not org_id:
            # Use the first organization if not specified
            try:
                organization = Organization.objects.first()
                if not organization:
                    raise CommandError('No organizations found. Please create an organization first.')
            except Organization.DoesNotExist:
                raise CommandError('No organizations found. Please create an organization first.')
        else:
            try:
                organization = Organization.objects.get(pk=org_id)
            except Organization.DoesNotExist:
                raise CommandError(f'Organization with ID {org_id} does not exist')
        
        # Prepare test data
        source_type = options.get('source')
        event_type = options.get('event')
        subject = options.get('subject')
        message = options.get('message')
        
        data = {
            'subject': subject,
            'message': message,
            'source_type': source_type,
            'event_type': event_type,
            'test': True,
            'timestamp': timezone.now().isoformat(),
            'source_id': 'test-1',
            'command_line': True
        }
        
        # Process the notification event
        self.stdout.write(f'Sending test notification to organization: {organization.name}')
        self.stdout.write(f'Event type: {event_type}')
        self.stdout.write(f'Source type: {source_type}')
        self.stdout.write(f'Data: {json.dumps(data, indent=2)}')
        
        logs = NotificationService.process_event(
            event_type=event_type,
            source_type=source_type,
            source_id='test-1',
            data=data,
            organization=organization
        )
        
        # Report on notification status
        if logs:
            self.stdout.write(self.style.SUCCESS(f'Successfully sent {len(logs)} notifications'))
            for log in logs:
                status = 'SUCCESS' if log.status == 'success' else 'FAILED'
                self.stdout.write(f'  - [{status}] To: {log.destination.name} ({log.destination.get_type_display()})')
                if log.status == 'failed':
                    self.stdout.write(self.style.ERROR(f'    Error: {log.error_message}'))
        else:
            self.stdout.write(self.style.WARNING('No matching notification rules found for this event'))
            self.stdout.write('Create notification rules in the admin interface or via the UI.') 