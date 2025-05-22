from celery import shared_task
import logging
import traceback
from django.utils import timezone
from datetime import timedelta
import requests
import json
from django.db import transaction

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def update_mitre_attack_data(self, url=None, preserve=False):
    """
    Update MITRE ATT&CK data from the official STIX data.
    
    Args:
        url (str, optional): URL to the MITRE ATT&CK STIX data JSON file.
            Defaults to the official Enterprise ATT&CK STIX data.
        preserve (bool, optional): Whether to preserve existing data. Defaults to False.
    """
    from core.models import MitreTactic, MitreTechnique, MitreSubTechnique
    
    if url is None:
        url = 'https://github.com/mitre-attack/attack-stix-data/raw/refs/heads/master/enterprise-attack/enterprise-attack.json'
    
    logger.info(f"Starting MITRE ATT&CK data update from {url}")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        stix_data = response.json()
        logger.info("Successfully downloaded MITRE ATT&CK data")
        
        # Process the STIX data within a transaction for atomicity
        with transaction.atomic():
            # Clear existing data unless preserve flag is set
            if not preserve:
                # Delete in correct order to respect foreign key constraints
                sub_count = MitreSubTechnique.objects.count()
                MitreSubTechnique.objects.all().delete()
                logger.info(f"Deleted {sub_count} sub-techniques")
                
                # Clear many-to-many relationships before deleting techniques
                for technique in MitreTechnique.objects.all():
                    technique.tactics.clear()
                    
                tech_count = MitreTechnique.objects.count()
                MitreTechnique.objects.all().delete()
                logger.info(f"Deleted {tech_count} techniques")
                
                tactic_count = MitreTactic.objects.count()
                MitreTactic.objects.all().delete()
                logger.info(f"Deleted {tactic_count} tactics")
            
            # Process and import STIX data
            process_stix_data(stix_data)
            
        logger.info("MITRE ATT&CK data update completed successfully")
        return {
            "status": "success",
            "message": "MITRE ATT&CK data updated successfully"
        }
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Error fetching MITRE ATT&CK data: {str(e)}"
        logger.error(error_msg)
        raise self.retry(exc=e)
    except json.JSONDecodeError:
        error_msg = "Error parsing MITRE ATT&CK JSON data"
        logger.error(error_msg)
        raise
    except Exception as e:
        error_msg = f"Error processing MITRE ATT&CK data: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        raise

def process_stix_data(stix_data):
    """
    Process the STIX data to extract tactics, techniques, and sub-techniques.
    
    This is adapted from the import_mitre_data management command.
    """
    from core.models import MitreTactic, MitreTechnique, MitreSubTechnique
    
    if 'objects' not in stix_data:
        raise ValueError("Invalid STIX data: 'objects' key not found")
    
    objects = stix_data['objects']
    
    # Dictionaries to store tactics and techniques for reference
    tactics_dict = {}
    techniques_dict = {}
    
    # First pass: identify and create tactics
    for obj in objects:
        if obj.get('type') == 'x-mitre-tactic':
            external_references = obj.get('external_references', [])
            tactic_id = None
            url = None
            
            for ref in external_references:
                if ref.get('source_name') == 'mitre-attack':
                    tactic_id = ref.get('external_id')
                    url = ref.get('url')
                    break
            
            if not tactic_id:
                continue
            
            name = obj.get('name', '')
            description = obj.get('description', '')
            
            try:
                tactic = MitreTactic.objects.create(
                    tactic_id=tactic_id,
                    name=name,
                    description=description,
                    url=url or f'https://attack.mitre.org/tactics/{tactic_id}/'
                )
                
                tactics_dict[tactic.tactic_id] = tactic
                logger.info(f"Created tactic: {tactic_id} - {name}")
            except Exception as e:
                logger.error(f"Error creating tactic {tactic_id}: {str(e)}")
    
    # Second pass: create techniques and link to tactics
    for obj in objects:
        if obj.get('type') == 'attack-pattern':
            external_references = obj.get('external_references', [])
            technique_id = None
            url = None
            
            for ref in external_references:
                if ref.get('source_name') == 'mitre-attack':
                    technique_id = ref.get('external_id')
                    url = ref.get('url')
                    break
            
            if not technique_id:
                continue
            
            # Skip sub-techniques in this pass
            if '.' in technique_id:
                continue
            
            name = obj.get('name', '')
            description = obj.get('description', '')
            
            try:
                technique = MitreTechnique.objects.create(
                    technique_id=technique_id,
                    name=name,
                    description=description,
                    url=url or f'https://attack.mitre.org/techniques/{technique_id}/'
                )
                
                # Get kill chain phases (tactics)
                kill_chain_phases = obj.get('kill_chain_phases', [])
                tactic_count = 0
                
                for phase in kill_chain_phases:
                    if phase.get('kill_chain_name') == 'mitre-attack':
                        phase_name = phase.get('phase_name')
                        # Find the corresponding tactic ID
                        for t_id, tactic in tactics_dict.items():
                            if phase_name.lower() == tactic.name.lower().replace(' ', '-'):
                                technique.tactics.add(tactic)
                                tactic_count += 1
                
                techniques_dict[technique_id] = technique
                logger.info(f"Created technique: {technique_id} - {name} (linked to {tactic_count} tactics)")
            except Exception as e:
                logger.error(f"Error creating technique {technique_id}: {str(e)}")
    
    # Third pass: create sub-techniques and link to parent techniques
    for obj in objects:
        if obj.get('type') == 'attack-pattern':
            external_references = obj.get('external_references', [])
            technique_id = None
            url = None
            
            for ref in external_references:
                if ref.get('source_name') == 'mitre-attack':
                    technique_id = ref.get('external_id')
                    url = ref.get('url')
                    break
            
            if not technique_id or '.' not in technique_id:
                continue
            
            parent_id = technique_id.split('.')[0]
            
            if parent_id not in techniques_dict:
                logger.warning(f"Parent technique {parent_id} not found for sub-technique {technique_id}")
                continue
                
            parent_technique = techniques_dict[parent_id]
            name = obj.get('name', '')
            description = obj.get('description', '')
            
            try:
                subtechnique = MitreSubTechnique.objects.create(
                    sub_technique_id=technique_id,
                    name=name,
                    description=description,
                    parent_technique=parent_technique,
                    url=url or f'https://attack.mitre.org/techniques/{technique_id}/'
                )
                
                logger.info(f"Created sub-technique: {technique_id} - {name}")
            except Exception as e:
                logger.error(f"Error creating sub-technique {technique_id}: {str(e)}")


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def enrich_observable(self, observable_id):
    """
    Enrich an observable with data from threat intelligence sources.
    
    Args:
        observable_id (int): Observable ID to enrich
    """
    from core.models import Observable
    
    logger.info(f"Starting enrichment for observable ID: {observable_id}")
    
    try:
        observable = Observable.objects.get(id=observable_id)
        
        # Update last_seen timestamp
        observable.last_seen = timezone.now()
        
        # Enrichment logic will depend on observable type
        if observable.type == Observable.IP:
            enriched_data = enrich_ip_observable(observable.value)
        elif observable.type == Observable.DOMAIN:
            enriched_data = enrich_domain_observable(observable.value)
        elif observable.type == Observable.URL:
            enriched_data = enrich_url_observable(observable.value)
        elif observable.type in [Observable.HASH_MD5, Observable.HASH_SHA1, Observable.HASH_SHA256]:
            enriched_data = enrich_hash_observable(observable.value, observable.type)
        else:
            logger.info(f"No enrichment available for observable type: {observable.type}")
            enriched_data = {}
        
        # If malicious indicators found in enrichment, update the observable
        if enriched_data.get('is_malicious', False):
            observable.is_malicious = True
            
            # Update confidence based on enrichment data
            if enriched_data.get('confidence') in [Observable.LOW, Observable.MEDIUM, Observable.HIGH]:
                observable.confidence = enriched_data['confidence']
            
            # Add enrichment data to description if available
            if enriched_data.get('description'):
                if observable.description:
                    observable.description += f"\n\nEnrichment data ({timezone.now().strftime('%Y-%m-%d %H:%M')}): {enriched_data['description']}"
                else:
                    observable.description = f"Enrichment data ({timezone.now().strftime('%Y-%m-%d %H:%M')}): {enriched_data['description']}"
        
        observable.save()
        logger.info(f"Observable ID {observable_id} enriched successfully")
        
        return {
            "status": "success",
            "observable_id": observable_id,
            "is_malicious": observable.is_malicious,
            "enrichment_data": enriched_data
        }
        
    except Observable.DoesNotExist:
        logger.error(f"Observable ID {observable_id} not found")
        return {"status": "error", "message": f"Observable ID {observable_id} not found"}
    except Exception as e:
        error_msg = f"Error enriching observable ID {observable_id}: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        raise self.retry(exc=e)

def enrich_ip_observable(ip_value):
    """
    Enrich an IP observable with threat intelligence data.
    
    In a production environment, this would query real threat intelligence APIs.
    """
    # This is a placeholder function - in a real environment, you would
    # call threat intelligence APIs or services here.
    logger.info(f"Enriching IP: {ip_value}")
    
    # Sample enrichment - replace with actual API calls to threat intelligence services
    return {
        "is_malicious": False,
        "confidence": None,
        "description": "No threat intelligence data available for this IP at this time."
    }

def enrich_domain_observable(domain_value):
    """Enrich a domain observable with threat intelligence data."""
    logger.info(f"Enriching domain: {domain_value}")
    
    # Sample enrichment - replace with actual API calls
    return {
        "is_malicious": False,
        "confidence": None,
        "description": "No threat intelligence data available for this domain at this time."
    }

def enrich_url_observable(url_value):
    """Enrich a URL observable with threat intelligence data."""
    logger.info(f"Enriching URL: {url_value}")
    
    # Sample enrichment - replace with actual API calls
    return {
        "is_malicious": False,
        "confidence": None,
        "description": "No threat intelligence data available for this URL at this time."
    }

def enrich_hash_observable(hash_value, hash_type):
    """Enrich a hash observable with threat intelligence data."""
    logger.info(f"Enriching {hash_type} hash: {hash_value}")
    
    # Sample enrichment - replace with actual API calls
    return {
        "is_malicious": False,
        "confidence": None,
        "description": f"No threat intelligence data available for this {hash_type} at this time."
    }


@shared_task
def cleanup_old_observables(days=90, dry_run=False):
    """
    Clean up old observables that haven't been seen in a specified number of days.
    
    Args:
        days (int): Number of days to consider an observable as "old"
        dry_run (bool): If True, only log what would be deleted without actually deleting
    """
    from core.models import Observable
    
    cutoff_date = timezone.now() - timedelta(days=days)
    logger.info(f"Finding observables not seen since {cutoff_date}")
    
    # Find observables that haven't been seen since the cutoff date
    # Only consider those that are not marked as malicious and have low confidence
    old_observables = Observable.objects.filter(
        last_seen__lt=cutoff_date,
        is_malicious=False,
        confidence=Observable.LOW
    )
    
    count = old_observables.count()
    logger.info(f"Found {count} old observables to clean up")
    
    # If dry run, just log what would be deleted
    if dry_run:
        logger.info("Dry run mode - no observables will be deleted")
        for observable in old_observables:
            logger.info(f"Would delete: {observable.id} - {observable.type}:{observable.value}")
        return {
            "status": "success",
            "dry_run": True,
            "count": count,
            "message": f"Found {count} observables that would be deleted"
        }
    
    # Delete the old observables
    old_observables.delete()
    logger.info(f"Deleted {count} old observables")
    
    return {
        "status": "success",
        "dry_run": False,
        "count": count,
        "message": f"Deleted {count} old observables"
    }


@shared_task
def analyze_observables_correlation():
    """
    Analyze observables to find correlations across cases.
    
    This task looks for observables that appear in multiple cases and
    logs potential relationships that might indicate connected incidents.
    """
    from core.models import Observable
    from django.db.models import Count
    
    logger.info("Starting observable correlation analysis")
    
    # Find observables that appear in multiple cases
    correlated_observables = Observable.objects.annotate(
        case_count=Count('cases')
    ).filter(
        case_count__gt=1
    ).order_by('-case_count')
    
    correlation_count = correlated_observables.count()
    logger.info(f"Found {correlation_count} observables appearing in multiple cases")
    
    # Log the correlations
    results = []
    for observable in correlated_observables:
        case_ids = list(observable.cases.values_list('id', flat=True))
        result = {
            "observable_id": observable.id,
            "observable_type": observable.type,
            "observable_value": observable.value,
            "case_count": observable.case_count,
            "case_ids": case_ids
        }
        results.append(result)
        logger.info(f"Observable {observable.type}:{observable.value} found in {observable.case_count} cases: {case_ids}")
    
    return {
        "status": "success",
        "correlation_count": correlation_count,
        "correlations": results
    }


@shared_task
def enrich_recent_observables(days=1):
    """
    Enrich observables that were created or updated within the specified number of days.
    
    Args:
        days (int): Number of days to look back for recent observables
    """
    from core.models import Observable
    
    # Calculate cutoff date for recent observables
    cutoff_date = timezone.now() - timedelta(days=days)
    logger.info(f"Finding observables created/updated since {cutoff_date}")
    
    # Find observables created or updated in the last 'days' days
    recent_observables = Observable.objects.filter(
        updated_at__gte=cutoff_date
    )
    
    count = recent_observables.count()
    logger.info(f"Found {count} observables to enrich")
    
    # Limit to a reasonable number to prevent overwhelming the system
    max_to_process = 100
    if count > max_to_process:
        logger.warning(f"Limiting enrichment to {max_to_process} observables")
        recent_observables = recent_observables.order_by('-updated_at')[:max_to_process]
        count = max_to_process
    
    # Enrich each observable
    for observable in recent_observables:
        # Use the existing enrich_observable task asynchronously
        enrich_observable.delay(observable.id)
    
    return {
        "status": "success",
        "count": count,
        "message": f"Scheduled enrichment for {count} observables"
    } 