from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _
from django.db import transaction

from organizations.models import Organization
from cases.models import ThreatCategory, TaskTemplate


class Command(BaseCommand):
    help = 'Create default task templates for each threat category'

    def add_arguments(self, parser):
        parser.add_argument(
            '--org',
            help='Organization name (default is SentinelIQ)',
            default='SentinelIQ'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update of existing templates'
        )

    def handle(self, *args, **options):
        org_name = options['org']
        force = options.get('force', False)
        self.stdout.write(f'Creating default task templates for {org_name}...')
        
        try:
            org = Organization.objects.get(name=org_name)
        except Organization.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Organization {org_name} not found'))
            return
        
        with transaction.atomic():
            self.create_task_templates(org, force)
        
        self.stdout.write(self.style.SUCCESS('Task templates created successfully!'))
    
    def create_task_templates(self, org, force=False):
        """Create default task templates for each threat category"""
        # Get all threat categories
        categories = ThreatCategory.objects.all()
        templates_created = 0
        
        # Se estiver forçando atualização, limpar templates existentes
        if force:
            self.stdout.write("Forcing template update - removing existing templates for organization")
            # Não excluímos as categorias, apenas os templates
            count = TaskTemplate.objects.filter(organization=org).delete()[0]
            self.stdout.write(f"Removed {count} existing templates")
        
        # Template for Phishing
        if ThreatCategory.objects.filter(name=ThreatCategory.PHISHING).exists():
            phishing = ThreatCategory.objects.get(name=ThreatCategory.PHISHING)
            templates = [
                {
                    'title': 'Verificar domínio de origem',
                    'description': 'Verificar se o domínio do e-mail de phishing é legítimo ou se trata-se de um domínio malicioso/falsificado.',
                    'priority': TaskTemplate.HIGH,
                    'order': 1,
                    'due_days': 1
                },
                {
                    'title': 'Verificar anexos/URLs',
                    'description': 'Analisar anexos ou URLs contidos no e-mail de phishing para identificação de malware ou páginas fraudulentas.',
                    'priority': TaskTemplate.HIGH,
                    'order': 2,
                    'due_days': 1
                },
                {
                    'title': 'Identificar usuários impactados',
                    'description': 'Levantar lista de usuários que receberam o e-mail e verificar se algum interagiu com o conteúdo malicioso.',
                    'priority': TaskTemplate.MEDIUM,
                    'order': 3,
                    'due_days': 2
                },
                {
                    'title': 'Bloquear remetente',
                    'description': 'Bloquear o remetente do e-mail de phishing em sistemas de e-mail e filtros anti-spam.',
                    'priority': TaskTemplate.MEDIUM,
                    'order': 4,
                    'due_days': 1
                },
                {
                    'title': 'Comunicar usuários',
                    'description': 'Enviar comunicado aos usuários sobre a tentativa de phishing e orientações de segurança.',
                    'priority': TaskTemplate.MEDIUM,
                    'order': 5,
                    'due_days': 3
                }
            ]
            
            for template_data in templates:
                template = TaskTemplate.objects.create(
                    organization=org,
                    threat_category=phishing,
                    title=template_data['title'],
                    description=template_data['description'],
                    priority=template_data['priority'],
                    order=template_data['order'],
                    due_days=template_data['due_days'],
                    is_active=True
                )
                
                templates_created += 1
                self.stdout.write(f'Created template: {template.title} for {phishing}')
        
        # Templates for Malware
        if ThreatCategory.objects.filter(name=ThreatCategory.MALWARE).exists():
            malware = ThreatCategory.objects.get(name=ThreatCategory.MALWARE)
            templates = [
                {
                    'title': 'Identificar malware',
                    'description': 'Identificar o tipo e família do malware através de análise de assinaturas e comportamentos.',
                    'priority': TaskTemplate.HIGH,
                    'order': 1,
                    'due_days': 1
                },
                {
                    'title': 'Isolar sistemas afetados',
                    'description': 'Isolar os sistemas afetados da rede para evitar propagação do malware.',
                    'priority': TaskTemplate.HIGH,
                    'order': 2,
                    'due_days': 1
                },
                {
                    'title': 'Investigar vetor de infecção',
                    'description': 'Determinar como o malware entrou no ambiente (e-mail, download, mídia removível, exploração de vulnerabilidade, etc.).',
                    'priority': TaskTemplate.MEDIUM,
                    'order': 3,
                    'due_days': 2
                },
                {
                    'title': 'Realizar varredura completa',
                    'description': 'Executar varredura anti-malware/antivírus em todos os sistemas potencialmente afetados.',
                    'priority': TaskTemplate.MEDIUM,
                    'order': 4,
                    'due_days': 2
                },
                {
                    'title': 'Remover malware e recuperar sistemas',
                    'description': 'Limpar o malware dos sistemas afetados e restaurar para estado seguro.',
                    'priority': TaskTemplate.HIGH,
                    'order': 5,
                    'due_days': 3
                }
            ]
            
            for template_data in templates:
                template = TaskTemplate.objects.create(
                    organization=org,
                    threat_category=malware,
                    title=template_data['title'],
                    description=template_data['description'],
                    priority=template_data['priority'],
                    order=template_data['order'],
                    due_days=template_data['due_days'],
                    is_active=True
                )
                
                templates_created += 1
                self.stdout.write(f'Created template: {template.title} for {malware}')
        
        # Templates for Ransomware
        if ThreatCategory.objects.filter(name=ThreatCategory.RANSOMWARE).exists():
            ransomware = ThreatCategory.objects.get(name=ThreatCategory.RANSOMWARE)
            templates = [
                {
                    'title': 'Isolar sistemas comprometidos',
                    'description': 'Isolar imediatamente todos os sistemas comprometidos para evitar a propagação do ransomware.',
                    'priority': TaskTemplate.HIGH,
                    'order': 1,
                    'due_days': 1
                },
                {
                    'title': 'Identificar ransomware',
                    'description': 'Identificar a variante de ransomware e verificar se existem ferramentas de descriptografia disponíveis.',
                    'priority': TaskTemplate.HIGH,
                    'order': 2,
                    'due_days': 1
                },
                {
                    'title': 'Acionar plano de continuidade',
                    'description': 'Ativar procedimentos de continuidade de negócios e recuperação de desastres.',
                    'priority': TaskTemplate.HIGH,
                    'order': 3,
                    'due_days': 1
                },
                {
                    'title': 'Avaliar extensão do comprometimento',
                    'description': 'Determinar quais sistemas foram afetados e o impacto ao negócio.',
                    'priority': TaskTemplate.MEDIUM,
                    'order': 4,
                    'due_days': 2
                },
                {
                    'title': 'Restaurar backups',
                    'description': 'Restaurar dados a partir de backups validados após limpar os sistemas afetados.',
                    'priority': TaskTemplate.HIGH,
                    'order': 5,
                    'due_days': 3
                },
                {
                    'title': 'Coordenar resposta legal',
                    'description': 'Contatar equipe jurídica e avaliar obrigações de notificação e comunicação com autoridades.',
                    'priority': TaskTemplate.MEDIUM,
                    'order': 6,
                    'due_days': 2
                }
            ]
            
            for template_data in templates:
                template = TaskTemplate.objects.create(
                    organization=org,
                    threat_category=ransomware,
                    title=template_data['title'],
                    description=template_data['description'],
                    priority=template_data['priority'],
                    order=template_data['order'],
                    due_days=template_data['due_days'],
                    is_active=True
                )
                
                templates_created += 1
                self.stdout.write(f'Created template: {template.title} for {ransomware}')
        
        # Templates for DDoS
        if ThreatCategory.objects.filter(name=ThreatCategory.DDoS).exists():
            ddos = ThreatCategory.objects.get(name=ThreatCategory.DDoS)
            templates = [
                {
                    'title': 'Identificar padrão de ataque',
                    'description': 'Analisar logs e tráfego para identificar o tipo e padrão do ataque DDoS.',
                    'priority': TaskTemplate.HIGH,
                    'order': 1,
                    'due_days': 1
                },
                {
                    'title': 'Ativar mitigação DDoS',
                    'description': 'Ativar mecanismos de mitigação como serviços anti-DDoS, WAF ou balanceadores de carga.',
                    'priority': TaskTemplate.HIGH,
                    'order': 2,
                    'due_days': 1
                },
                {
                    'title': 'Implementar regras de filtragem',
                    'description': 'Configurar regras de filtragem na borda da rede para bloquear o tráfego malicioso.',
                    'priority': TaskTemplate.HIGH,
                    'order': 3,
                    'due_days': 1
                },
                {
                    'title': 'Escalar capacidade',
                    'description': 'Aumentar capacidade de infraestrutura ou ativar recursos de auto-scaling para absorver o tráfego.',
                    'priority': TaskTemplate.MEDIUM,
                    'order': 4,
                    'due_days': 2
                },
                {
                    'title': 'Comunicar partes interessadas',
                    'description': 'Informar equipes internas, clientes e parceiros sobre o incidente e expectativas de resolução.',
                    'priority': TaskTemplate.MEDIUM,
                    'order': 5,
                    'due_days': 1
                },
                {
                    'title': 'Documentar IOCs do ataque',
                    'description': 'Registrar IPs, padrões de tráfego e outros indicadores do ataque para análise posterior e bloqueio preventivo.',
                    'priority': TaskTemplate.LOW,
                    'order': 6,
                    'due_days': 3
                }
            ]
            
            for template_data in templates:
                template = TaskTemplate.objects.create(
                    organization=org,
                    threat_category=ddos,
                    title=template_data['title'],
                    description=template_data['description'],
                    priority=template_data['priority'],
                    order=template_data['order'],
                    due_days=template_data['due_days'],
                    is_active=True
                )
                
                templates_created += 1
                self.stdout.write(f'Created template: {template.title} for {ddos}')
        
        # Summary
        self.stdout.write(f'Created {templates_created} task templates for {org.name}') 