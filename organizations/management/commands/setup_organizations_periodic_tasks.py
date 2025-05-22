from django.core.management.base import BaseCommand
from django.utils import timezone
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
import json
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Configure Celery Beat periodic tasks for the organizations module'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreate tasks, removing existing ones with the same names'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Configuring organizations module periodic tasks'))
        
        force = options.get('force', False)
        if force:
            self._clean_existing_tasks()
        
        # Configure common interval schedules
        weekly = self._get_or_create_interval_schedule(IntervalSchedule.DAYS, 7)
        monthly = self._get_or_create_interval_schedule(IntervalSchedule.DAYS, 30)
        quarterly = self._get_or_create_interval_schedule(IntervalSchedule.DAYS, 90)
        
        # Configure crontab schedules
        # Every Monday at 5:00 AM
        monday_5am = self._get_or_create_crontab_schedule(
            minute=0, hour=5, day_of_week='1', day_of_month='*', month_of_year='*'
        )
        # Every 1st of the month at 3:00 AM
        first_day_3am = self._get_or_create_crontab_schedule(
            minute=0, hour=3, day_of_week='*', day_of_month='1', month_of_year='*'
        )
        # Every Sunday at 2:00 AM
        sunday_2am = self._get_or_create_crontab_schedule(
            minute=0, hour=2, day_of_week='0', day_of_month='*', month_of_year='*'
        )
        # First day of each quarter at 4:00 AM
        quarterly_4am = self._get_or_create_crontab_schedule(
            minute=0, hour=4, day_of_week='*', day_of_month='1', month_of_year='1,4,7,10'
        )
        
        # 1. Check inactive organizations - run weekly on Monday at 5:00 AM
        self._create_periodic_task(
            name='Check Inactive Organizations',
            task='organizations.tasks.check_inactive_organizations',
            schedule=monday_5am,
            kwargs=json.dumps({}),
            description='Identify organizations without recent activity and notify administrators'
        )
        
        # 2. Generate organization metrics - run monthly on the 1st at 3:00 AM
        self._create_periodic_task(
            name='Generate Organization Metrics',
            task='organizations.tasks.generate_organization_metrics',
            schedule=first_day_3am,
            kwargs=json.dumps({}),
            description='Generate and email monthly metrics reports for all organizations'
        )
        
        # 3. Cleanup inactive organizations - run quarterly on the 1st day at 4:00 AM
        self._create_periodic_task(
            name='Cleanup Inactive Organizations',
            task='organizations.tasks.cleanup_inactive_organizations',
            schedule=quarterly_4am,
            kwargs=json.dumps({}),
            description='Archive or clean up data for long-term inactive organizations'
        )
        
        # 4. Verify organization data integrity - run weekly on Sunday at 2:00 AM
        self._create_periodic_task(
            name='Verify Organization Data Integrity',
            task='organizations.tasks.verify_organization_data_integrity',
            schedule=sunday_2am,
            kwargs=json.dumps({}),
            description='Verify data integrity across organizations and report issues'
        )
        
        self.stdout.write(self.style.SUCCESS('Successfully configured organizations module periodic tasks'))

    def _clean_existing_tasks(self):
        """Clean existing periodic tasks with the same names"""
        task_names = [
            'Check Inactive Organizations',
            'Generate Organization Metrics',
            'Cleanup Inactive Organizations',
            'Verify Organization Data Integrity'
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