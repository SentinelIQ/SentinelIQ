from django.core.management.base import BaseCommand
from django.utils import timezone
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
import json
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Configure Celery Beat periodic tasks for the core module'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreate tasks, removing existing ones with the same names'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Configuring core module periodic tasks'))
        
        force = options.get('force', False)
        if force:
            self._clean_existing_tasks()
        
        # Configure common interval schedules
        hourly = self._get_or_create_interval_schedule(IntervalSchedule.HOURS, 1)
        daily = self._get_or_create_interval_schedule(IntervalSchedule.DAYS, 1)
        weekly = self._get_or_create_interval_schedule(IntervalSchedule.DAYS, 7)
        monthly = self._get_or_create_interval_schedule(IntervalSchedule.DAYS, 30)
        
        # Configure crontab schedules
        midnight = self._get_or_create_crontab_schedule(
            minute=0, hour=0, day_of_week='*', day_of_month='*', month_of_year='*'
        )
        every_six_hours = self._get_or_create_crontab_schedule(
            minute=0, hour='*/6', day_of_week='*', day_of_month='*', month_of_year='*'
        )
        sunday_midnight = self._get_or_create_crontab_schedule(
            minute=0, hour=0, day_of_week='0', day_of_month='*', month_of_year='*'
        )
        first_day_of_month = self._get_or_create_crontab_schedule(
            minute=0, hour=0, day_of_week='*', day_of_month='1', month_of_year='*'
        )
        
        # 1. MITRE ATT&CK data update - weekly on Sunday at midnight
        self._create_periodic_task(
            name='Update MITRE ATT&CK data',
            task='core.tasks.update_mitre_attack_data',
            schedule=sunday_midnight,
            kwargs=json.dumps({'preserve': False}),
            description='Updates MITRE ATT&CK tactics, techniques, and sub-techniques from official STIX data'
        )
        
        # 2. Analyze observable correlations - daily at midnight
        self._create_periodic_task(
            name='Analyze observable correlations',
            task='core.tasks.analyze_observables_correlation',
            schedule=midnight,
            kwargs=json.dumps({}),
            description='Analyzes observables to identify correlations across cases'
        )
        
        # 3. Clean up old observables - first day of each month
        self._create_periodic_task(
            name='Clean up old observables',
            task='core.tasks.cleanup_old_observables',
            schedule=first_day_of_month,
            kwargs=json.dumps({'days': 90, 'dry_run': False}),
            description='Removes old, low-confidence, non-malicious observables that have not been seen in 90+ days'
        )
        
        # 4. Enrich new observables - placeholder for a periodic task that would enrich recent observables
        # In a real implementation, this would likely be triggered by a signal when a new observable is created
        # rather than running periodically on all observables
        self._create_periodic_task(
            name='Enrich recent observables',
            task='core.tasks.enrich_recent_observables',
            schedule=every_six_hours,
            kwargs=json.dumps({'days': 1}),
            description='Enriches observables created or updated in the last day with threat intelligence data'
        )
        
        self.stdout.write(self.style.SUCCESS('Successfully configured core module periodic tasks'))

    def _clean_existing_tasks(self):
        """Clean existing periodic tasks with the same names"""
        task_names = [
            'Update MITRE ATT&CK data',
            'Analyze observable correlations',
            'Clean up old observables',
            'Enrich recent observables'
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