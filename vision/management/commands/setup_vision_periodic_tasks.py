from django.core.management.base import BaseCommand
from django.utils import timezone
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
import json
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Configure Celery Beat periodic tasks for the Vision module'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreate tasks, removing existing ones with the same names'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Configuring Vision module periodic tasks'))
        
        force = options.get('force', False)
        if force:
            self.stdout.write('Force flag specified. Removing existing tasks.')
            self._remove_existing_tasks()
        
        # Create or update the tasks
        self._setup_misp_sync_task()
        self._setup_observable_enrichment_task()
        self._setup_threat_intel_cleanup_task()
        self._setup_weekly_report_task()
        self._setup_case_enrichment_task()
        
        self.stdout.write(self.style.SUCCESS('Successfully configured Vision module periodic tasks'))

    def _remove_existing_tasks(self):
        """Remove all existing Vision module tasks"""
        tasks = PeriodicTask.objects.filter(task__startswith='vision.tasks.')
        count = tasks.count()
        tasks.delete()
        self.stdout.write(f'Removed {count} existing Vision tasks')

    def _setup_misp_sync_task(self):
        """Set up the MISP synchronization task"""
        # This task should run every hour
        interval, created = IntervalSchedule.objects.get_or_create(
            every=60,
            period=IntervalSchedule.MINUTES,
        )
        
        task_name = 'Sync MISP Instances'
        task, created = PeriodicTask.objects.get_or_create(
            name=task_name,
            defaults={
                'interval': interval,
                'task': 'vision.tasks.sync_all_misp_instances',
                'kwargs': json.dumps({}),
                'enabled': True,
                'description': 'Synchronize active MISP instances based on their configured frequency'
            }
        )
        
        if not created:
            # Update existing task
            task.interval = interval
            task.enabled = True
            task.save()
            self.stdout.write(f'Updated existing task: {task_name}')
        else:
            self.stdout.write(f'Created new task: {task_name}')

    def _setup_observable_enrichment_task(self):
        """Set up the automatic observable enrichment task"""
        # This task should run every 2 hours
        interval, created = IntervalSchedule.objects.get_or_create(
            every=120,
            period=IntervalSchedule.MINUTES,
        )
        
        task_name = 'Enrich New Observables'
        task, created = PeriodicTask.objects.get_or_create(
            name=task_name,
            defaults={
                'interval': interval,
                'task': 'vision.tasks.enrich_new_observables',
                'kwargs': json.dumps({}),
                'enabled': True,
                'description': 'Automatically enrich new observables with threat intelligence data'
            }
        )
        
        if not created:
            # Update existing task
            task.interval = interval
            task.enabled = True
            task.save()
            self.stdout.write(f'Updated existing task: {task_name}')
        else:
            self.stdout.write(f'Created new task: {task_name}')

    def _setup_threat_intel_cleanup_task(self):
        """Set up the threat intelligence cleanup task"""
        # This task should run weekly on Sunday at 1 AM
        crontab, created = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='1',
            day_of_week='0',
            day_of_month='*',
            month_of_year='*',
        )
        
        task_name = 'Cleanup Old Threat Intel'
        task, created = PeriodicTask.objects.get_or_create(
            name=task_name,
            defaults={
                'crontab': crontab,
                'task': 'vision.tasks.cleanup_old_threat_intel',
                'kwargs': json.dumps({}),
                'enabled': True,
                'description': 'Mark or archive old threat intelligence items'
            }
        )
        
        if not created:
            # Update existing task
            task.crontab = crontab
            task.enabled = True
            task.save()
            self.stdout.write(f'Updated existing task: {task_name}')
        else:
            self.stdout.write(f'Created new task: {task_name}')

    def _setup_weekly_report_task(self):
        """Set up the weekly threat intelligence report task"""
        # This task should run every Monday at 7 AM
        crontab, created = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='7',
            day_of_week='1',
            day_of_month='*',
            month_of_year='*',
        )
        
        task_name = 'Generate Weekly Threat Intel Report'
        task, created = PeriodicTask.objects.get_or_create(
            name=task_name,
            defaults={
                'crontab': crontab,
                'task': 'vision.tasks.generate_threat_intel_report',
                'kwargs': json.dumps({}),
                'enabled': True,
                'description': 'Generate and send weekly threat intelligence reports'
            }
        )
        
        if not created:
            # Update existing task
            task.crontab = crontab
            task.enabled = True
            task.save()
            self.stdout.write(f'Updated existing task: {task_name}')
        else:
            self.stdout.write(f'Created new task: {task_name}')

    def _setup_case_enrichment_task(self):
        """Set up the automatic case enrichment task"""
        # This task should run daily at 3 AM
        crontab, created = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='3',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
        )
        
        task_name = 'Auto Enrich Cases'
        task, created = PeriodicTask.objects.get_or_create(
            name=task_name,
            defaults={
                'crontab': crontab,
                'task': 'vision.tasks.auto_enrich_cases',
                'kwargs': json.dumps({}),
                'enabled': True,
                'description': 'Automatically enrich cases with threat intelligence data'
            }
        )
        
        if not created:
            # Update existing task
            task.crontab = crontab
            task.enabled = True
            task.save()
            self.stdout.write(f'Updated existing task: {task_name}')
        else:
            self.stdout.write(f'Created new task: {task_name}') 