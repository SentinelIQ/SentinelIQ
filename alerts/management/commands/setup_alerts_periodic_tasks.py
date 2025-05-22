from django.core.management.base import BaseCommand
from django.utils import timezone
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
import json
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Configure Celery Beat periodic tasks for the alerts module'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreate tasks, removing existing ones with the same names'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Configuring alerts module periodic tasks'))
        
        force = options.get('force', False)
        if force:
            self._clean_existing_tasks()
        
        # Configure common interval schedules
        hourly = self._get_or_create_interval_schedule(IntervalSchedule.HOURS, 1)
        daily = self._get_or_create_interval_schedule(IntervalSchedule.DAYS, 1)
        weekly = self._get_or_create_interval_schedule(IntervalSchedule.DAYS, 7)
        
        # Configure crontab schedules
        # Every day at 7:00 AM
        morning_seven = self._get_or_create_crontab_schedule(
            minute=0, hour=7, day_of_week='*', day_of_month='*', month_of_year='*'
        )
        # Every 3 hours
        every_three_hours = self._get_or_create_crontab_schedule(
            minute=0, hour='*/3', day_of_week='*', day_of_month='*', month_of_year='*'
        )
        # Every Sunday at 11:00 PM
        sunday_night = self._get_or_create_crontab_schedule(
            minute=0, hour=23, day_of_week='0', day_of_month='*', month_of_year='*'
        )
        
        # 1. Process aging alerts - run daily at 7:00 AM
        self._create_periodic_task(
            name='Process Aging Alerts',
            task='alerts.tasks.process_aging_alerts',
            schedule=morning_seven,
            kwargs=json.dumps({}),
            description='Auto-close resolved alerts and notify about stale alerts'
        )
        
        # 2. Auto-escalate critical alerts - run every 3 hours
        self._create_periodic_task(
            name='Auto-Escalate Critical Alerts',
            task='alerts.tasks.auto_escalate_critical_alerts',
            schedule=every_three_hours,
            kwargs=json.dumps({}),
            description='Automatically escalate critical alerts to cases'
        )
        
        # 3. Generate alert statistics - run weekly on Sunday night
        self._create_periodic_task(
            name='Generate Alert Statistics',
            task='alerts.tasks.generate_alert_statistics',
            schedule=sunday_night,
            kwargs=json.dumps({}),
            description='Generate statistics and insights from alert data'
        )
        
        self.stdout.write(self.style.SUCCESS('Successfully configured alerts module periodic tasks'))

    def _clean_existing_tasks(self):
        """Clean existing periodic tasks with the same names"""
        task_names = [
            'Process Aging Alerts',
            'Auto-Escalate Critical Alerts',
            'Generate Alert Statistics'
        ]
        
        for name in task_names:
            deleted_count, _ = PeriodicTask.objects.filter(name=name).delete()
            if deleted_count:
                self.stdout.write(f"Removed existing task: {name}")

    def _get_or_create_interval_schedule(self, period, every):
        """Get or create an interval schedule"""
        schedule, created = IntervalSchedule.objects.get_or_create(
            period=period,
            every=every
        )
        if created:
            logger.info(f"Created interval schedule: {period} {every}")
        return schedule

    def _get_or_create_crontab_schedule(self, minute, hour, day_of_week, day_of_month, month_of_year):
        """Get or create a crontab schedule"""
        schedule, created = CrontabSchedule.objects.get_or_create(
            minute=minute,
            hour=hour,
            day_of_week=day_of_week,
            day_of_month=day_of_month,
            month_of_year=month_of_year
        )
        if created:
            logger.info(f"Created crontab schedule: {minute} {hour} {day_of_week} {day_of_month} {month_of_year}")
        return schedule

    def _create_periodic_task(self, name, task, schedule, kwargs=None, description=''):
        """Create a periodic task"""
        if not kwargs:
            kwargs = '{}'
        
        # First delete any existing task with the same name to avoid conflicts
        PeriodicTask.objects.filter(name=name).delete()
        
        # Create the task with the appropriate schedule type
        task_defaults = {
            'task': task,
            'kwargs': kwargs,
            'description': description,
            'enabled': True,
            'one_off': False,
        }
        
        # Set the appropriate schedule type
        if isinstance(schedule, IntervalSchedule):
            task_defaults['interval'] = schedule
        elif isinstance(schedule, CrontabSchedule):
            task_defaults['crontab'] = schedule
        
        # Create the task with all fields set at once
        periodic_task = PeriodicTask.objects.create(
            name=name,
            **task_defaults
        )
        
        self.stdout.write(f"Created periodic task: {name}") 