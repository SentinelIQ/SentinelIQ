from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.text import slugify
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from organizations.models import Organization
from accounts.models import User
from cases.models import ThreatCategory

User = get_user_model()

class Command(BaseCommand):
    help = 'Initialize the system with basic data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            default='admin',
            help='Username for the superadmin',
        )
        parser.add_argument(
            '--password',
            default='admin123',
            help='Password for the superadmin',
        )
        parser.add_argument(
            '--email',
            default='admin@example.com',
            help='Email for the superadmin',
        )
        parser.add_argument(
            '--org-name',
            default='Default Organization',
            help='Name for the default organization',
        )

    def handle(self, *args, **kwargs):
        self.stdout.write('Inicializando o sistema...')
        self.create_default_organization()
        self.create_superadmin()
        self.create_threat_categories()
        self.stdout.write('System initialization complete!')
    
    def create_default_organization(self):
        """Create the default organization if it doesn't exist"""
        org, created = Organization.objects.get_or_create(
            name="SentinelIQ",
            defaults={
                'description': "Default organization for SentinelIQ",
                'created_at': timezone.now()
            }
        )
        
        if created:
            self.stdout.write('Default organization created')
        else:
            self.stdout.write('Organization SentinelIQ already exists')
    
    def create_superadmin(self):
        """Create a superuser if it doesn't exist"""
        try:
            User.objects.get(username='admin')
            self.stdout.write('Superadmin admin already exists')
        except User.DoesNotExist:
            org = Organization.objects.get(name="SentinelIQ")
            
            User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123',
                organization=org,
                first_name='System',
                last_name='Administrator'
            )
            self.stdout.write('Superadmin admin created')
    
    def create_threat_categories(self):
        """Create default threat categories if they don't exist"""
        # Define icon classes for each threat category
        icons = {
            ThreatCategory.PHISHING: 'fa-fish',
            ThreatCategory.MALWARE: 'fa-bug',
            ThreatCategory.RANSOMWARE: 'fa-lock',
            ThreatCategory.DATA_BREACH: 'fa-database',
            ThreatCategory.INSIDER_THREAT: 'fa-user-secret',
            ThreatCategory.DDoS: 'fa-server',
            ThreatCategory.UNAUTHORIZED_ACCESS: 'fa-user-lock',
            ThreatCategory.SOCIAL_ENGINEERING: 'fa-users-cog',
            ThreatCategory.SUPPLY_CHAIN: 'fa-truck',
            ThreatCategory.OTHER: 'fa-question-circle',
        }
        
        # Define descriptions for each threat category
        descriptions = {
            ThreatCategory.PHISHING: 'Ataques que utilizam comunicações fraudulentas para enganar os destinatários e levá-los a revelar informações sensíveis ou instalar malware.',
            ThreatCategory.MALWARE: 'Software malicioso projetado para infiltrar, danificar ou obter acesso não autorizado a sistemas de computador.',
            ThreatCategory.RANSOMWARE: 'Tipo de malware que criptografa dados e exige pagamento para descriptografá-los.',
            ThreatCategory.DATA_BREACH: 'Exposição não autorizada de informações sensíveis, confidenciais ou protegidas.',
            ThreatCategory.INSIDER_THREAT: 'Ameaças originárias de pessoas dentro da organização que têm informações privilegiadas sobre práticas, dados e sistemas de segurança.',
            ThreatCategory.DDoS: 'Ataques que visam tornar um serviço online indisponível sobrecarregando-o com tráfego de múltiplas fontes.',
            ThreatCategory.UNAUTHORIZED_ACCESS: 'Acesso a sistemas, redes ou dados sem permissão adequada.',
            ThreatCategory.SOCIAL_ENGINEERING: 'Manipulação psicológica de pessoas para realizar ações ou divulgar informações confidenciais.',
            ThreatCategory.SUPPLY_CHAIN: 'Ataques que comprometem sistemas por meio de fornecedores ou parceiros externos.',
            ThreatCategory.OTHER: 'Outras ameaças que não se enquadram nas categorias padrão.',
        }
        
        # Create all threat categories
        categories_created = 0
        for category_type, display_name in ThreatCategory.CATEGORY_CHOICES:
            category, created = ThreatCategory.objects.get_or_create(
                name=category_type,
                defaults={
                    'description': descriptions.get(category_type, ''),
                    'icon_class': icons.get(category_type, 'fa-shield-alt'),
                }
            )
            if created:
                categories_created += 1
        
        if categories_created > 0:
            self.stdout.write(f'Created {categories_created} threat categories')
        else:
            self.stdout.write('All threat categories already exist') 