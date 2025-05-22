from django.core.management.base import BaseCommand
from django.utils import timezone
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
import json
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Configure Celery Beat periodic tasks for the cases module'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreate tasks, removing existing ones with the same names'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Configuring cases module periodic tasks'))
        
        force = options.get('force', False)
        if force:
            self._clean_existing_tasks()
        
        # Configure common interval schedules
        hourly = self._get_or_create_interval_schedule(IntervalSchedule.HOURS, 1)
        daily = self._get_or_create_interval_schedule(IntervalSchedule.DAYS, 1)
        weekly = self._get_or_create_interval_schedule(IntervalSchedule.DAYS, 7)
        monthly = self._get_or_create_interval_schedule(IntervalSchedule.DAYS, 30)
        
        # Configure crontab schedules
        # Every day at 8:00 AM
        morning_notification = self._get_or_create_crontab_schedule(
            minute=0, hour=8, day_of_week='*', day_of_month='*', month_of_year='*'
        )
        # Every Monday at midnight
        monday_midnight = self._get_or_create_crontab_schedule(
            minute=0, hour=0, day_of_week='1', day_of_month='*', month_of_year='*'
        )
        # First day of each month at 2:00 AM
        monthly_archive = self._get_or_create_crontab_schedule(
            minute=0, hour=2, day_of_week='*', day_of_month='1', month_of_year='*'
        )
        
        # 1. Task to send notifications for overdue tasks - every day at 8:00 AM
        self._create_periodic_task(
            name='Notify Overdue Tasks',
            task='cases.tasks.notify_overdue_tasks',
            schedule=morning_notification,
            kwargs=json.dumps({}),
            description='Sends email notifications for tasks that are overdue'
        )
        
        # 2. Case data analysis - weekly on Monday at midnight
        self._create_periodic_task(
            name='Analyze Case Data',
            task='cases.tasks.analyze_case_data',
            schedule=monday_midnight,
            kwargs=json.dumps({}),
            description='Analyzes case data to identify patterns and trends'
        )
        
        # 3. Archive old cases - monthly on the 1st at 2:00 AM (dry run mode by default)
        self._create_periodic_task(
            name='Archive Old Cases',
            task='cases.tasks.archive_old_cases',
            schedule=monthly_archive,
            kwargs=json.dumps({
                'days': 90,
                'status': ['closed'],
                'dry_run': True
            }),
            description='Archives cases that have been closed for more than 90 days (dry run)'
        )
        
        self.stdout.write(self.style.SUCCESS('Successfully configured cases module periodic tasks'))

    def _clean_existing_tasks(self):
        """Clean existing periodic tasks with the same names"""
        task_names = [
            'Notify Overdue Tasks',
            'Analyze Case Data',
            'Archive Old Cases'
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