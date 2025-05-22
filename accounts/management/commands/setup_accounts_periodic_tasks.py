from django.core.management.base import BaseCommand
from django.utils import timezone
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
import json
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Configure Celery Beat periodic tasks for the accounts module'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreate tasks, removing existing ones with the same names'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Configuring accounts module periodic tasks'))
        
        force = options.get('force', False)
        if force:
            self._clean_existing_tasks()
        
        # Configure common interval schedules
        daily = self._get_or_create_interval_schedule(IntervalSchedule.DAYS, 1)
        weekly = self._get_or_create_interval_schedule(IntervalSchedule.DAYS, 7)
        monthly = self._get_or_create_interval_schedule(IntervalSchedule.DAYS, 30)
        
        # Configure crontab schedules
        # Every day at 1:00 AM
        daily_1am = self._get_or_create_crontab_schedule(
            minute=0, hour=1, day_of_week='*', day_of_month='*', month_of_year='*'
        )
        # Every Monday at 6:00 AM
        monday_6am = self._get_or_create_crontab_schedule(
            minute=0, hour=6, day_of_week='1', day_of_month='*', month_of_year='*'
        )
        # Every day at 3:00 AM
        daily_3am = self._get_or_create_crontab_schedule(
            minute=0, hour=3, day_of_week='*', day_of_month='*', month_of_year='*'
        )
        # Every first day of month at 2:00 AM
        monthly_2am = self._get_or_create_crontab_schedule(
            minute=0, hour=2, day_of_week='*', day_of_month='1', month_of_year='*'
        )
        
        # 1. Check inactive users - run daily at 1:00 AM
        self._create_periodic_task(
            name='Check Inactive Users',
            task='accounts.tasks.check_inactive_users',
            schedule=daily_1am,
            kwargs=json.dumps({}),
            description='Identify inactive users and send notifications or deactivate accounts'
        )
        
        # 2. Generate user activity reports - run weekly on Monday at 6:00 AM
        self._create_periodic_task(
            name='Generate User Activity Reports',
            task='accounts.tasks.generate_user_activity_reports',
            schedule=monday_6am,
            kwargs=json.dumps({}),
            description='Generate and email weekly activity reports to organization admins'
        )
        
        # 3. Analyze login patterns - run daily at 3:00 AM
        self._create_periodic_task(
            name='Analyze Login Patterns',
            task='accounts.tasks.analyze_login_patterns',
            schedule=daily_3am,
            kwargs=json.dumps({}),
            description='Detect unusual login patterns and potential security issues'
        )
        
        # 4. Clean expired sessions - run monthly on the 1st at 2:00 AM
        self._create_periodic_task(
            name='Clean Expired Sessions',
            task='accounts.tasks.clean_expired_sessions',
            schedule=monthly_2am,
            kwargs=json.dumps({}),
            description='Remove expired sessions from the database'
        )
        
        self.stdout.write(self.style.SUCCESS('Successfully configured accounts module periodic tasks'))

    def _clean_existing_tasks(self):
        """Clean existing periodic tasks with the same names"""
        task_names = [
            'Check Inactive Users',
            'Generate User Activity Reports',
            'Analyze Login Patterns',
            'Clean Expired Sessions'
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