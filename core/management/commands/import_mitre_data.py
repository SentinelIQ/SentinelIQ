from django.core.management.base import BaseCommand
from core.models import MitreTactic, MitreTechnique, MitreSubTechnique
import requests
import json
from django.db import transaction

class Command(BaseCommand):
    help = 'Import MITRE ATT&CK data from official STIX data'
    
    def add_arguments(self, parser):
        parser.add_argument('--url', type=str, default='https://github.com/mitre-attack/attack-stix-data/raw/refs/heads/master/enterprise-attack/enterprise-attack.json',
                            help='URL to the MITRE ATT&CK STIX data JSON file')
        parser.add_argument('--preserve', action='store_true', help='Preserve existing data (default is to delete all before import)')
    
    def handle(self, *args, **options):
        url = options['url']
        preserve = options['preserve']
        
        self.stdout.write(f'Fetching MITRE ATT&CK data from {url}...')
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            stix_data = response.json()
            self.stdout.write(self.style.SUCCESS('Successfully downloaded MITRE ATT&CK data'))
            
            # Process the STIX data within a transaction for atomicity
            with transaction.atomic():
                # Clear existing data unless preserve flag is set
                if not preserve:
                    self._clear_existing_data()
                
                self._process_stix_data(stix_data)
                
            self.stdout.write(self.style.SUCCESS('MITRE ATT&CK data import completed!'))
            
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f'Error fetching data: {str(e)}'))
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR('Error parsing JSON data'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error processing data: {str(e)}'))
    
    def _clear_existing_data(self):
        """Remove all existing MITRE data"""
        self.stdout.write('Removing existing MITRE data...')
        
        # Delete in correct order to respect foreign key constraints
        sub_count = MitreSubTechnique.objects.count()
        MitreSubTechnique.objects.all().delete()
        self.stdout.write(f'Deleted {sub_count} sub-techniques')
        
        # Clear many-to-many relationships before deleting techniques
        for technique in MitreTechnique.objects.all():
            technique.tactics.clear()
            
        tech_count = MitreTechnique.objects.count()
        MitreTechnique.objects.all().delete()
        self.stdout.write(f'Deleted {tech_count} techniques')
        
        tactic_count = MitreTactic.objects.count()
        MitreTactic.objects.all().delete()
        self.stdout.write(f'Deleted {tactic_count} tactics')
    
    def _process_stix_data(self, stix_data):
        """Process the STIX data to extract tactics, techniques, and sub-techniques"""
        if 'objects' not in stix_data:
            raise ValueError("Invalid STIX data: 'objects' key not found")
        
        objects = stix_data['objects']
        
        # Dictionaries to store tactics and techniques for reference
        tactics_dict = {}
        techniques_dict = {}
        
        # First pass: identify and create tactics and techniques
        self.stdout.write('Processing tactics and techniques...')
        
        # Process tactics
        tactic_count = 0
        for obj in objects:
            if obj.get('type') == 'x-mitre-tactic':
                tactic = self._process_tactic(obj)
                if tactic:
                    tactic_count += 1
                    tactics_dict[tactic.tactic_id] = tactic
        
        # Process techniques and subtechniques
        technique_count = 0
        subtechnique_count = 0
        
        for obj in objects:
            if obj.get('type') == 'attack-pattern':
                external_references = obj.get('external_references', [])
                technique_id = None
                
                for ref in external_references:
                    if ref.get('source_name') == 'mitre-attack':
                        technique_id = ref.get('external_id')
                        break
                
                if not technique_id:
                    continue
                
                # Check if it's a sub-technique
                if '.' in technique_id:
                    subtechnique = self._process_subtechnique(obj, technique_id, techniques_dict)
                    if subtechnique:
                        subtechnique_count += 1
                else:
                    technique = self._process_technique(obj, technique_id, tactics_dict)
                    if technique:
                        technique_count += 1
                        techniques_dict[technique_id] = technique
        
        self.stdout.write(self.style.SUCCESS(f'Processed {tactic_count} tactics, {technique_count} techniques, and {subtechnique_count} sub-techniques'))
    
    def _process_tactic(self, tactic_obj):
        """Process a tactic object and create the database record"""
        external_references = tactic_obj.get('external_references', [])
        tactic_id = None
        url = None
        
        for ref in external_references:
            if ref.get('source_name') == 'mitre-attack':
                tactic_id = ref.get('external_id')
                url = ref.get('url')
                break
        
        if not tactic_id:
            return None
        
        name = tactic_obj.get('name', '')
        description = tactic_obj.get('description', '')
        
        try:
            tactic = MitreTactic.objects.create(
                tactic_id=tactic_id,
                name=name,
                description=description,
                url=url or f'https://attack.mitre.org/tactics/{tactic_id}/'
            )
            
            self.stdout.write(self.style.SUCCESS(f'Created tactic: {tactic_id} - {name}'))
            return tactic
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating tactic {tactic_id}: {str(e)}'))
            return None
    
    def _process_technique(self, technique_obj, technique_id, tactics_dict):
        """Process a technique object and create the database record"""
        name = technique_obj.get('name', '')
        description = technique_obj.get('description', '')
        
        external_references = technique_obj.get('external_references', [])
        url = None
        
        for ref in external_references:
            if ref.get('source_name') == 'mitre-attack':
                url = ref.get('url')
                break
        
        try:
            technique = MitreTechnique.objects.create(
                technique_id=technique_id,
                name=name,
                description=description,
                url=url or f'https://attack.mitre.org/techniques/{technique_id}/'
            )
            
            # Get kill chain phases (tactics)
            kill_chain_phases = technique_obj.get('kill_chain_phases', [])
            tactic_count = 0
            
            for phase in kill_chain_phases:
                if phase.get('kill_chain_name') == 'mitre-attack':
                    phase_name = phase.get('phase_name')
                    # Find the corresponding tactic ID
                    for t_id, tactic in tactics_dict.items():
                        if phase_name.lower() == tactic.name.lower().replace(' ', '-'):
                            technique.tactics.add(tactic)
                            tactic_count += 1
            
            self.stdout.write(self.style.SUCCESS(f'Created technique: {technique_id} - {name} (linked to {tactic_count} tactics)'))
            return technique
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating technique {technique_id}: {str(e)}'))
            return None
    
    def _process_subtechnique(self, subtechnique_obj, subtechnique_id, techniques_dict):
        """Process a sub-technique object and create the database record"""
        parent_id = subtechnique_id.split('.')[0]
        
        if parent_id not in techniques_dict:
            self.stdout.write(self.style.WARNING(f'Parent technique {parent_id} not found for sub-technique {subtechnique_id}'))
            return None
            
        parent_technique = techniques_dict[parent_id]
        name = subtechnique_obj.get('name', '')
        description = subtechnique_obj.get('description', '')
        
        external_references = subtechnique_obj.get('external_references', [])
        url = None
        
        for ref in external_references:
            if ref.get('source_name') == 'mitre-attack':
                url = ref.get('url')
                break
        
        try:
            subtechnique = MitreSubTechnique.objects.create(
                sub_technique_id=subtechnique_id,
                name=name,
                description=description,
                parent_technique=parent_technique,
                url=url or f'https://attack.mitre.org/techniques/{subtechnique_id}/'
            )
            
            self.stdout.write(self.style.SUCCESS(f'Created sub-technique: {subtechnique_id} - {name}'))
            return subtechnique
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating sub-technique {subtechnique_id}: {str(e)}'))
            return None 