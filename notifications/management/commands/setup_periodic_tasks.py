from django.core.management.base import BaseCommand
from django.utils import timezone
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
import json
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Configurar tarefas periódicas no Celery Beat para o sistema de notificações'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Configurando tarefas periódicas do Celery Beat'))
        
        # Limpar tarefas antigas com o mesmo nome
        self._clean_existing_tasks()
        
        # Configurar intervalos comuns
        hourly = self._get_or_create_interval_schedule(IntervalSchedule.HOURS, 1)
        daily = self._get_or_create_interval_schedule(IntervalSchedule.DAYS, 1)
        weekly = self._get_or_create_interval_schedule(IntervalSchedule.DAYS, 7)
        
        # Configurar cronograma crontab
        midnight = self._get_or_create_crontab_schedule(
            minute=0, hour=0, day_of_week='*', day_of_month='*', month_of_year='*'
        )
        every_five_minutes = self._get_or_create_crontab_schedule(
            minute='*/5', hour='*', day_of_week='*', day_of_month='*', month_of_year='*'
        )
        every_thirty_minutes = self._get_or_create_crontab_schedule(
            minute='*/30', hour='*', day_of_week='*', day_of_month='*', month_of_year='*'
        )
        
        # 1. Limpar logs antigos diariamente à meia-noite
        self._create_periodic_task(
            name='Limpar logs antigos de notificações',
            task='notifications.tasks.clean_old_notification_logs',
            schedule=midnight,
            kwargs=json.dumps({'days': 30}),
            description='Remove logs de notificações com mais de 30 dias'
        )
        
        # 2. Limpar eventos antigos uma vez por semana
        self._create_periodic_task(
            name='Limpar eventos antigos de notificações',
            task='notifications.tasks.cleanup_notification_events',
            schedule=weekly,
            kwargs=json.dumps({'events_days': 60, 'logs_days': 90, 'keep_errors': True}),
            description='Remove eventos de notificações antigos e processados'
        )
        
        # 3. Gerar estatísticas a cada hora
        self._create_periodic_task(
            name='Gerar estatísticas de notificações',
            task='notifications.tasks.generate_notification_statistics',
            schedule=hourly,
            description='Gerar estatísticas de notificações para o painel'
        )
        
        # 4. Reenviar notificações falhas a cada 30 minutos
        self._create_periodic_task(
            name='Reenviar notificações falhas',
            task='notifications.tasks.retry_failed_notifications',
            schedule=every_thirty_minutes,
            kwargs=json.dumps({'max_retries': 3, 'hours': 24}),
            description='Tentar novamente enviar notificações que falharam'
        )
        
        # 5. Monitorar saúde do sistema de notificações a cada 5 minutos
        self._create_periodic_task(
            name='Monitorar saúde das notificações',
            task='notifications.tasks.monitor_notification_health',
            schedule=every_five_minutes,
            description='Verificar a saúde do sistema de notificações e alertar se necessário'
        )
        
        self.stdout.write(self.style.SUCCESS('Tarefas periódicas configuradas com sucesso!'))
    
    def _clean_existing_tasks(self):
        """Limpar tarefas agendadas anteriores para evitar duplicação"""
        task_names = [
            'Limpar logs antigos de notificações',
            'Limpar eventos antigos de notificações',
            'Gerar estatísticas de notificações',
            'Reenviar notificações falhas',
            'Monitorar saúde das notificações'
        ]
        
        deleted, _ = PeriodicTask.objects.filter(name__in=task_names).delete()
        if deleted:
            self.stdout.write(f'  - Removidas {deleted} tarefas existentes')
    
    def _get_or_create_interval_schedule(self, period, every):
        """Obter ou criar um intervalo de agendamento"""
        schedule, created = IntervalSchedule.objects.get_or_create(
            period=period,
            every=every,
        )
        action = 'Criado' if created else 'Usando existente'
        self.stdout.write(f'  - {action} intervalo de {every} {period}')
        return schedule
    
    def _get_or_create_crontab_schedule(self, minute, hour, day_of_week, day_of_month, month_of_year):
        """Obter ou criar um agendamento crontab"""
        schedule, created = CrontabSchedule.objects.get_or_create(
            minute=minute,
            hour=hour,
            day_of_week=day_of_week,
            day_of_month=day_of_month,
            month_of_year=month_of_year,
        )
        action = 'Criado' if created else 'Usando existente'
        self.stdout.write(f'  - {action} crontab {minute} {hour} {day_of_week} {day_of_month} {month_of_year}')
        return schedule
    
    def _create_periodic_task(self, name, task, schedule, kwargs=None, description=None):
        """Criar uma tarefa periódica"""
        task = PeriodicTask.objects.create(
            name=name,
            task=task,
            interval=schedule if isinstance(schedule, IntervalSchedule) else None,
            crontab=schedule if isinstance(schedule, CrontabSchedule) else None,
            kwargs=kwargs or '{}',
            description=description or '',
            enabled=True,
        )
        self.stdout.write(f'  - Criada tarefa periódica: {name}')
        return task 