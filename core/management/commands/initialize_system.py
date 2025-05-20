from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from organizations.models import Organization
from accounts.models import User


class Command(BaseCommand):
    help = 'Initialize the system with default organization and superadmin user'

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

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        email = options['email']
        org_name = options['org_name']
        
        with transaction.atomic():
            # Create default organization if it doesn't exist
            org_slug = slugify(org_name)
            organization, org_created = Organization.objects.get_or_create(
                slug=org_slug,
                defaults={
                    'name': org_name,
                    'description': 'Default organization created during system initialization',
                    'is_active': True,
                }
            )
            
            if org_created:
                self.stdout.write(self.style.SUCCESS(f'Created default organization: {org_name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Organization {org_name} already exists'))
            
            # Create superadmin if it doesn't exist
            if not User.objects.filter(username=username).exists():
                User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password,
                    organization=organization,
                    role=User.SUPERADMIN,
                    is_staff=True,
                    is_superuser=True,
                )
                self.stdout.write(self.style.SUCCESS(f'Created superadmin user: {username}'))
            else:
                user = User.objects.get(username=username)
                if not user.is_superuser:
                    user.is_superuser = True
                    user.is_staff = True
                    user.role = User.SUPERADMIN
                    user.organization = organization
                    user.save()
                    self.stdout.write(self.style.SUCCESS(f'Updated user {username} to superadmin'))
                else:
                    self.stdout.write(self.style.WARNING(f'Superadmin {username} already exists'))
            
            self.stdout.write(self.style.SUCCESS('System initialization complete!')) 