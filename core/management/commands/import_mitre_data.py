from django.core.management.base import BaseCommand
from core.models import MitreTactic, MitreTechnique, MitreSubTechnique

class Command(BaseCommand):
    help = 'Import basic MITRE ATT&CK data'

    def handle(self, *args, **options):
        self.stdout.write('Importing MITRE ATT&CK data...')
        
        # Create tactics
        tactics = {
            'TA0001': 'Initial Access',
            'TA0002': 'Execution',
            'TA0003': 'Persistence',
            'TA0004': 'Privilege Escalation',
            'TA0005': 'Defense Evasion',
            'TA0006': 'Credential Access',
            'TA0007': 'Discovery',
            'TA0008': 'Lateral Movement',
            'TA0009': 'Collection',
            'TA0010': 'Exfiltration',
            'TA0011': 'Command and Control',
            'TA0040': 'Impact',
            'TA0042': 'Resource Development',
            'TA0043': 'Reconnaissance',
        }
        
        tactic_objs = {}
        for tactic_id, name in tactics.items():
            tactic, created = MitreTactic.objects.get_or_create(
                tactic_id=tactic_id,
                defaults={
                    'name': name,
                    'url': f'https://attack.mitre.org/tactics/{tactic_id}/'
                }
            )
            tactic_objs[tactic_id] = tactic
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created tactic: {tactic_id} - {name}'))
            else:
                self.stdout.write(f'Tactic already exists: {tactic_id} - {name}')
        
        # Create techniques
        techniques = {
            'T1566': {
                'name': 'Phishing',
                'tactics': ['TA0001'],
            },
            'T1190': {
                'name': 'Exploit Public-Facing Application',
                'tactics': ['TA0001'],
            },
            'T1133': {
                'name': 'External Remote Services',
                'tactics': ['TA0001'],
            },
            'T1059': {
                'name': 'Command and Scripting Interpreter',
                'tactics': ['TA0002'],
            },
            'T1053': {
                'name': 'Scheduled Task/Job',
                'tactics': ['TA0002', 'TA0003', 'TA0004'],
            },
            'T1078': {
                'name': 'Valid Accounts',
                'tactics': ['TA0001', 'TA0003', 'TA0004', 'TA0005', 'TA0008'],
            },
            'T1140': {
                'name': 'Deobfuscate/Decode Files or Information',
                'tactics': ['TA0005'],
            },
            'T1110': {
                'name': 'Brute Force',
                'tactics': ['TA0006'],
            },
            'T1087': {
                'name': 'Account Discovery',
                'tactics': ['TA0007'],
            },
            'T1021': {
                'name': 'Remote Services',
                'tactics': ['TA0008'],
            },
            'T1560': {
                'name': 'Archive Collected Data',
                'tactics': ['TA0009'],
            },
            'T1048': {
                'name': 'Exfiltration Over Alternative Protocol',
                'tactics': ['TA0010'],
            },
            'T1071': {
                'name': 'Application Layer Protocol',
                'tactics': ['TA0011'],
            },
            'T1485': {
                'name': 'Data Destruction',
                'tactics': ['TA0040'],
            },
            'T1583': {
                'name': 'Acquire Infrastructure',
                'tactics': ['TA0042'],
            },
            'T1595': {
                'name': 'Active Scanning',
                'tactics': ['TA0043'],
            },
        }
        
        technique_objs = {}
        for technique_id, data in techniques.items():
            technique, created = MitreTechnique.objects.get_or_create(
                technique_id=technique_id,
                defaults={
                    'name': data['name'],
                    'url': f'https://attack.mitre.org/techniques/{technique_id}/'
                }
            )
            
            # Add tactics
            for tactic_id in data['tactics']:
                if tactic_id in tactic_objs:
                    technique.tactics.add(tactic_objs[tactic_id])
            
            technique_objs[technique_id] = technique
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created technique: {technique_id} - {data["name"]}'))
            else:
                self.stdout.write(f'Technique already exists: {technique_id} - {data["name"]}')
        
        # Create sub-techniques
        subtechniques = {
            'T1566.001': {
                'name': 'Spearphishing Attachment',
                'parent': 'T1566',
            },
            'T1566.002': {
                'name': 'Spearphishing Link',
                'parent': 'T1566',
            },
            'T1059.001': {
                'name': 'PowerShell',
                'parent': 'T1059',
            },
            'T1059.003': {
                'name': 'Windows Command Shell',
                'parent': 'T1059',
            },
            'T1059.005': {
                'name': 'Visual Basic',
                'parent': 'T1059',
            },
            'T1059.007': {
                'name': 'JavaScript',
                'parent': 'T1059',
            },
            'T1078.001': {
                'name': 'Default Accounts',
                'parent': 'T1078',
            },
            'T1078.002': {
                'name': 'Domain Accounts',
                'parent': 'T1078',
            },
            'T1078.003': {
                'name': 'Local Accounts',
                'parent': 'T1078',
            },
            'T1110.001': {
                'name': 'Password Guessing',
                'parent': 'T1110',
            },
            'T1110.002': {
                'name': 'Password Cracking',
                'parent': 'T1110',
            },
            'T1110.003': {
                'name': 'Password Spraying',
                'parent': 'T1110',
            },
            'T1021.001': {
                'name': 'Remote Desktop Protocol',
                'parent': 'T1021',
            },
            'T1021.002': {
                'name': 'SMB/Windows Admin Shares',
                'parent': 'T1021',
            },
            'T1021.006': {
                'name': 'Windows Remote Management',
                'parent': 'T1021',
            },
        }
        
        for subtechnique_id, data in subtechniques.items():
            parent_id = data['parent']
            if parent_id in technique_objs:
                subtechnique, created = MitreSubTechnique.objects.get_or_create(
                    sub_technique_id=subtechnique_id,
                    defaults={
                        'name': data['name'],
                        'parent_technique': technique_objs[parent_id],
                        'url': f'https://attack.mitre.org/techniques/{subtechnique_id}/'
                    }
                )
                
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created sub-technique: {subtechnique_id} - {data["name"]}'))
                else:
                    self.stdout.write(f'Sub-technique already exists: {subtechnique_id} - {data["name"]}')
        
        self.stdout.write(self.style.SUCCESS('MITRE ATT&CK data import completed!')) 