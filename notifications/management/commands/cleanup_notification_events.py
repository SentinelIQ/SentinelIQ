from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from notifications.models import NotificationEvent, NotificationLog
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Limpar eventos antigos de notificação'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--events-days', 
            type=int, 
            default=30, 
            help='Remover eventos mais antigos que N dias (padrão: 30)'
        )
        parser.add_argument(
            '--logs-days', 
            type=int, 
            default=90, 
            help='Remover logs mais antigos que N dias (padrão: 90)'
        )
        parser.add_argument(
            '--keep-errors', 
            action='store_true', 
            help='Manter logs com status de erro mesmo que sejam antigos'
        )
        parser.add_argument(
            '--dry-run', 
            action='store_true', 
            help='Apenas mostrar o que seria removido sem excluir nada'
        )
    
    def handle(self, *args, **options):
        events_days = options['events_days']
        logs_days = options['logs_days']
        keep_errors = options['keep_errors']
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.SUCCESS('Iniciando limpeza de notificações antigas'))
        
        # Timestamp de corte para eventos
        events_cutoff = timezone.now() - timezone.timedelta(days=events_days)
        
        # Encontrar eventos antigos
        old_events = NotificationEvent.objects.filter(
            created_at__lte=events_cutoff,
            processed=True  # Só limpamos eventos já processados
        )
        
        # Contar eventos antigos
        old_events_count = old_events.count()
        self.stdout.write(f'Eventos antigos encontrados: {old_events_count}')
        
        # Remover eventos antigos
        if not dry_run and old_events_count > 0:
            old_events.delete()
            self.stdout.write(self.style.SUCCESS(f'Removidos {old_events_count} eventos antigos'))
        
        # Timestamp de corte para logs
        logs_cutoff = timezone.now() - timezone.timedelta(days=logs_days)
        
        # Filtrar logs antigos
        old_logs_query = NotificationLog.objects.filter(created_at__lte=logs_cutoff)
        
        # Se precisamos manter os erros, filtramos para excluí-los
        if keep_errors:
            old_logs_query = old_logs_query.exclude(status='failed')
        
        # Contar logs antigos
        old_logs_count = old_logs_query.count()
        self.stdout.write(f'Logs antigos encontrados: {old_logs_count}')
        
        # Remover logs antigos
        if not dry_run and old_logs_count > 0:
            old_logs_query.delete()
            self.stdout.write(self.style.SUCCESS(f'Removidos {old_logs_count} logs antigos'))
            
        if dry_run:
            self.stdout.write(self.style.WARNING('Modo simulação: nenhum dado foi removido'))
        
        self.stdout.write(self.style.SUCCESS('Limpeza concluída'))
            
        # Retornar contagens para possível uso programático
        return {
            'events_removed': old_events_count if not dry_run else 0,
            'logs_removed': old_logs_count if not dry_run else 0
        } 