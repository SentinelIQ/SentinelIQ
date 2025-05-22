from django.core.management.base import BaseCommand
from django.utils import timezone
import time
import logging
from celery.result import AsyncResult
from notifications.tasks import clean_old_notification_logs
from notifications.models import NotificationEvent, NotificationDestination, NotificationRule, NotificationLog

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Teste da integração do Celery com o sistema de notificações'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-test-notification',
            action='store_true',
            help='Criar e processar uma notificação de teste',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando teste do Celery'))
        
        # Teste básico de conectividade do Celery
        self.stdout.write('Enviando tarefa de teste para o Celery...')
        
        # Usar uma tarefa existente para testar conectividade
        task = clean_old_notification_logs.delay(days=365)  # Usando um valor alto para não excluir logs reais
        
        self.stdout.write(f'Tarefa enviada com ID: {task.id}')
        self.stdout.write('Aguardando o resultado da tarefa...')
        
        # Aguardar o resultado da tarefa
        time_waited = 0
        while not task.ready() and time_waited < 10:
            time.sleep(1)
            time_waited += 1
            self.stdout.write('.')
        
        if task.ready():
            self.stdout.write(self.style.SUCCESS(f'Tarefa concluída! Resultado: {task.result}'))
        else:
            self.stdout.write(self.style.WARNING('Tarefa ainda em execução após tempo limite. Verifique os logs do worker.'))
        
        # Criar e processar um evento de notificação de teste
        if options['create_test_notification']:
            self.create_test_notification()
    
    def create_test_notification(self):
        """Cria e processa um evento de notificação de teste"""
        from notifications.services import NotificationService
        
        self.stdout.write('\nCriando evento de notificação de teste...')
        
        # Verificar se existe pelo menos uma organização
        from organizations.models import Organization
        try:
            organization = Organization.objects.first()
            if not organization:
                self.stdout.write(self.style.ERROR('Nenhuma organização encontrada. Crie uma organização primeiro.'))
                return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erro ao buscar organização: {str(e)}'))
            return
        
        # Dados de exemplo para o evento
        event_data = {
            'source_id': 'test-123',
            'source_type': 'test',
            'event_type': 'created',
            'timestamp': timezone.now().isoformat(),
            'title': 'Evento de teste do Celery',
            'description': 'Este é um evento de teste para verificar a integração do Celery'
        }
        
        try:
            # Processar o evento
            event = NotificationService.process_event(
                event_type='created',
                source_type='test',
                source_id='test-123',
                data=event_data,
                organization=organization
            )
            
            self.stdout.write(self.style.SUCCESS(f'Evento criado com ID: {event.id}'))
            self.stdout.write('O evento será processado de forma assíncrona pelo worker Celery.')
            self.stdout.write('Aguarde alguns segundos e verifique os logs de notificação no sistema.')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erro ao processar evento: {str(e)}')) 