from django.core.management.base import BaseCommand
from django.utils import timezone
from vision.models import MISPInstance
from vision.services.misp import MISPService


class Command(BaseCommand):
    help = 'Sincroniza dados de todas as instâncias MISP ativas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forçar sincronização mesmo para instâncias sem o período mínimo desde a última sincronização',
        )
        parser.add_argument(
            '--id',
            type=int,
            help='Sincronizar apenas a instância MISP com o ID especificado',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        instance_id = options.get('id')
        
        if instance_id:
            try:
                instances = [MISPInstance.objects.get(pk=instance_id)]
                self.stdout.write(f"Sincronizando instância MISP específica: {instances[0].name}")
            except MISPInstance.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Instância MISP com ID {instance_id} não encontrada"))
                return
        else:
            # Obter todas as instâncias MISP ativas
            instances = MISPInstance.objects.filter(status__in=['active', 'pending'])
            self.stdout.write(f"Sincronizando {instances.count()} instâncias MISP")
        
        if not instances:
            self.stdout.write("Nenhuma instância MISP ativa para sincronizar")
            return
        
        total_items = 0
        success_count = 0
        error_count = 0
        
        for instance in instances:
            try:
                # Verificar se deve sincronizar com base na frequência configurada
                should_sync = force or (
                    not instance.last_sync or 
                    (timezone.now() - instance.last_sync).seconds / 60 >= instance.sync_frequency
                )
                
                if not should_sync:
                    self.stdout.write(f"Ignorando {instance.name} - sincronização recente")
                    continue
                
                self.stdout.write(f"Sincronizando {instance.name}...")
                
                service = MISPService(instance)
                items = service.sync()
                
                # Atualizar o status e o timestamp de sincronização
                instance.last_sync = timezone.now()
                instance.status = 'active'
                instance.save()
                
                self.stdout.write(
                    self.style.SUCCESS(f"Sincronização de {instance.name} concluída - {items} itens importados")
                )
                
                total_items += items
                success_count += 1
                
            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(f"Erro ao sincronizar {instance.name}: {str(e)}")
                )
                
                # Atualizar status para erro
                instance.status = 'error'
                instance.save()
                
                error_count += 1
        
        self.stdout.write("------------------------------------")
        self.stdout.write(f"Sincronização concluída:")
        self.stdout.write(f"  Total de instâncias: {len(instances)}")
        self.stdout.write(f"  Instâncias sincronizadas com sucesso: {success_count}")
        self.stdout.write(f"  Instâncias com erro: {error_count}")
        self.stdout.write(f"  Total de itens importados: {total_items}")
        self.stdout.write("------------------------------------") 