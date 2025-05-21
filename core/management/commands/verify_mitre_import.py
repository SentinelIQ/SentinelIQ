from django.core.management.base import BaseCommand
from django.db.models import Count
from core.models import MitreTactic, MitreTechnique, MitreSubTechnique

class Command(BaseCommand):
    help = 'Verify MITRE ATT&CK data import and relationships'
    
    def handle(self, *args, **options):
        # Verificar contagem de elementos
        tactics_count = MitreTactic.objects.count()
        techniques_count = MitreTechnique.objects.count()
        subtechniques_count = MitreSubTechnique.objects.count()
        
        self.stdout.write(self.style.SUCCESS(f'MITRE ATT&CK Database Status:'))
        self.stdout.write(f'Tactics: {tactics_count}')
        self.stdout.write(f'Techniques: {techniques_count}')
        self.stdout.write(f'Sub-techniques: {subtechniques_count}')
        
        # Verificar relações
        techniques_with_tactics = MitreTechnique.objects.annotate(
            tactics_count=Count('tactics')
        ).filter(tactics_count__gt=0).count()
        
        subtechniques_with_parents = MitreSubTechnique.objects.exclude(
            parent_technique=None
        ).count()
        
        self.stdout.write(f'\nRelationship Status:')
        self.stdout.write(f'Techniques with Tactics: {techniques_with_tactics} ({(techniques_with_tactics/techniques_count*100):.1f}% of total)')
        self.stdout.write(f'Sub-techniques with Parents: {subtechniques_with_parents} ({(subtechniques_with_parents/subtechniques_count*100):.1f}% of total)')
        
        # Verificar amostras
        self.stdout.write(f'\nSample Data:')
        
        # Amostra de táticas
        self.stdout.write(f'\nSample Tactics:')
        for tactic in MitreTactic.objects.all()[:5]:
            self.stdout.write(f'  - {tactic.tactic_id}: {tactic.name}')
            
        # Amostra de técnicas
        self.stdout.write(f'\nSample Techniques:')
        for technique in MitreTechnique.objects.all()[:5]:
            tactics = ", ".join([t.tactic_id for t in technique.tactics.all()])
            self.stdout.write(f'  - {technique.technique_id}: {technique.name}')
            self.stdout.write(f'    Related Tactics: {tactics or "None"}')
            
        # Amostra de sub-técnicas
        self.stdout.write(f'\nSample Sub-techniques:')
        for subtechnique in MitreSubTechnique.objects.all()[:5]:
            parent = subtechnique.parent_technique.technique_id if subtechnique.parent_technique else "None"
            self.stdout.write(f'  - {subtechnique.sub_technique_id}: {subtechnique.name}')
            self.stdout.write(f'    Parent Technique: {parent}')
            
        self.stdout.write(self.style.SUCCESS('\nVerification completed!')) 