from celery import shared_task
import logging
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from vision.models import MISPInstance, ThreatIntelligenceItem
from vision.services.misp import MISPService
from vision.services.misp_case_integration import MISPCaseIntegration
from cases.models import Case
from core.models import Observable

logger = logging.getLogger(__name__)

@shared_task
def sync_all_misp_instances():
    """
    Synchronize all active MISP instances based on their configured frequency.
    
    This task:
    1. Checks all active MISP instances
    2. Determines if they are due for synchronization based on their sync_frequency setting
    3. Performs synchronization for instances that are due
    """
    from vision.models import MISPInstance
    
    # Get all active MISP instances
    instances = MISPInstance.objects.filter(status__in=['active', 'pending'])
    
    if not instances:
        logger.info("No active MISP instances found for synchronization")
        return {'status': 'success', 'instances_synced': 0, 'items_imported': 0}
    
    now = timezone.now()
    instances_synced = 0
    total_items_imported = 0
    errors = []
    
    for instance in instances:
        try:
            # Check if the instance is due for synchronization
            should_sync = False
            if not instance.last_sync:
                should_sync = True
            else:
                # Calculate time since last sync in minutes
                time_since_sync = (now - instance.last_sync).total_seconds() / 60
                should_sync = time_since_sync >= instance.sync_frequency
            
            if not should_sync:
                logger.debug(f"Skipping MISP instance {instance.name} - not due for sync yet")
                continue
            
            logger.info(f"Synchronizing MISP instance: {instance.name}")
            
            # Perform synchronization
            service = MISPService(instance)
            items_imported = service.sync()
            
            # Update last sync time and status
            instance.last_sync = now
            instance.status = 'active'
            instance.save()
            
            instances_synced += 1
            total_items_imported += items_imported
            
            logger.info(f"Successfully synchronized MISP instance {instance.name}. "
                        f"Imported/updated {items_imported} items.")
        
        except Exception as e:
            # Log the error and continue with next instance
            error_msg = f"Error synchronizing MISP instance {instance.name}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
            
            # Update status to error
            instance.status = 'error'
            instance.save()
    
    result = {
        'status': 'success' if not errors else 'partial_success',
        'instances_synced': instances_synced,
        'items_imported': total_items_imported,
        'errors': errors
    }
    
    logger.info(f"MISP synchronization task completed: {instances_synced} instances synced, "
                f"{total_items_imported} items imported/updated")
    
    return result


@shared_task
def enrich_new_observables():
    """
    Automatically enrich new observables with threat intelligence data.
    
    This task:
    1. Finds observables that haven't been enriched with threat intelligence
    2. Checks for matching threat intelligence data
    3. Updates observables with enrichment data
    """
    from core.models import Observable
    
    # Find observables that haven't been checked for threat intel
    # Looking for recently created observables (last 24 hours) without enrichment flag
    time_threshold = timezone.now() - timedelta(hours=24)
    
    # Using two separate queries instead of combining with Q objects
    observables = Observable.objects.filter(
        created_at__gte=time_threshold
    ).exclude(
        description__icontains="Threat Intelligence from"
    ).select_related('organization')
    
    if not observables:
        logger.info("No new observables found for threat intelligence enrichment")
        return {'status': 'success', 'observables_checked': 0, 'observables_enriched': 0}
    
    observables_checked = 0
    observables_enriched = 0
    
    for observable in observables:
        try:
            # Find matching threat intelligence
            items = MISPCaseIntegration.find_threat_intel_for_observable(observable)
            observables_checked += 1
            
            if items:
                # Update observable with threat intel data
                observable.is_malicious = any(item.is_malicious for item in items)
                
                # Find highest confidence item
                confidence_mapping = {'high': 3, 'medium': 2, 'low': 1}
                # Fix: Pass lambda function first, then iterable
                highest_confidence = max(items, key=lambda x: confidence_mapping.get(x.confidence, 0))
                observable.confidence = highest_confidence.confidence
                
                # Add enrichment info to description
                if observable.description:
                    observable.description += "\n\n"
                else:
                    observable.description = ""
                
                observable.description += f"[Threat Intelligence from {highest_confidence.feed.name}]\n"
                observable.description += f"Confidence: {highest_confidence.get_confidence_display()}\n"
                
                if highest_confidence.tags:
                    observable.description += f"Tags: {highest_confidence.tags}\n"
                
                if highest_confidence.creator_org:
                    observable.description += f"Source: {highest_confidence.creator_org}\n"
                
                if highest_confidence.external_url:
                    observable.description += f"\nSource Link: {highest_confidence.external_url}"
                
                observable.save()
                observables_enriched += 1
                
                # If observable is associated with cases, add timeline event
                for case in observable.cases.all():
                    case.add_timeline_event(
                        event_type='threat_intel_added',
                        title=f"Threat Intelligence automatically added to {observable.get_type_display()}: {observable.value}",
                        description=f"Enriched with threat intelligence from {highest_confidence.feed.name}",
                        metadata={
                            'observable_id': observable.id,
                            'feed_name': highest_confidence.feed.name,
                            'is_malicious': observable.is_malicious
                        }
                    )
                
                logger.info(f"Enriched observable {observable.value} with threat intelligence data")
        
        except Exception as e:
            logger.error(f"Error enriching observable {observable.id}: {str(e)}")
    
    return {
        'status': 'success',
        'observables_checked': observables_checked,
        'observables_enriched': observables_enriched
    }


@shared_task
def cleanup_old_threat_intel():
    """
    Mark or archive old threat intelligence items.
    
    This task:
    1. Identifies threat intelligence items that haven't been updated in a long time
    2. Updates their status or archives them based on configured rules
    """
    # Define thresholds
    archive_threshold = timezone.now() - timedelta(days=365)  # 1 year
    update_threshold = timezone.now() - timedelta(days=90)    # 90 days
    
    # Find items that are candidates for archiving or updating
    old_items = ThreatIntelligenceItem.objects.filter(
        last_seen__lt=update_threshold
    )
    
    very_old_items = old_items.filter(
        last_seen__lt=archive_threshold
    )
    
    archived_count = 0
    updated_count = 0
    
    # For demonstration, we'll just update the very old items
    # In a real implementation, you might want to archive them to another table
    # or delete them depending on your retention policy
    for item in very_old_items:
        try:
            # Add archived flag in description
            if item.description:
                if "[ARCHIVED]" not in item.description:
                    item.description = "[ARCHIVED] " + item.description
            else:
                item.description = "[ARCHIVED] This threat intelligence item has been archived due to age."
            
            item.save()
            archived_count += 1
        except Exception as e:
            logger.error(f"Error archiving threat intel item {item.id}: {str(e)}")
    
    # For items that are old but not very old, update their confidence
    for item in old_items.exclude(last_seen__lt=archive_threshold):
        try:
            if item.confidence == 'high':
                item.confidence = 'medium'
                updated_count += 1
            elif item.confidence == 'medium':
                item.confidence = 'low'
                updated_count += 1
            # Low confidence items remain low
            
            item.save()
        except Exception as e:
            logger.error(f"Error updating confidence for threat intel item {item.id}: {str(e)}")
    
    logger.info(f"Threat intelligence cleanup completed: {archived_count} items archived, "
                f"{updated_count} items had confidence reduced")
    
    return {
        'status': 'success',
        'archived_count': archived_count,
        'updated_count': updated_count
    }


@shared_task
def generate_threat_intel_report():
    """
    Generate periodic reports on threat intelligence data.
    
    This task:
    1. Compiles statistics on recent threat intelligence
    2. Identifies trends and notable threats
    3. Generates a report for administrators
    """
    from django.contrib.auth import get_user_model
    from django.db.models import Count
    from organizations.models import Organization
    
    User = get_user_model()
    
    # Define reporting period
    report_period_start = timezone.now() - timedelta(days=7)  # Last 7 days
    
    # Collect statistics for the report
    stats = {}
    
    # Overall statistics
    new_items = ThreatIntelligenceItem.objects.filter(
        created_at__gte=report_period_start
    )
    stats['total_new_items'] = new_items.count()
    
    # Breakdown by type
    type_breakdown = new_items.values('item_type').annotate(
        count=Count('item_type')
    ).order_by('-count')
    stats['type_breakdown'] = list(type_breakdown)
    
    # Breakdown by malicious status
    malicious_count = new_items.filter(is_malicious=True).count()
    stats['malicious_count'] = malicious_count
    stats['benign_count'] = stats['total_new_items'] - malicious_count
    
    # Top tags
    all_tags = []
    for item in new_items.exclude(tags=''):
        if item.tags:
            for tag in item.tags.split(','):
                all_tags.append(tag.strip())
    
    tag_counts = {}
    for tag in all_tags:
        tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    # Fix: Place the lambda function first, then specify the key and reverse parameters
    stats['top_tags'] = sorted(
        [{'tag': tag, 'count': count} for tag, count in tag_counts.items()],
        key=lambda x: x['count'], 
        reverse=True
    )[:10]  # Top 10 tags
    
    # MISP synchronization status
    misp_instances = MISPInstance.objects.all()
    stats['misp_instances'] = [
        {
            'name': instance.name,
            'status': instance.status,
            'last_sync': instance.last_sync,
            'is_public': instance.is_public
        }
        for instance in misp_instances
    ]
    
    # Generate and send report for each organization
    for org in Organization.objects.all():
        try:
            # Get organization-specific stats
            org_items = new_items.filter(
                Q(feed__organization=org) | Q(feed__is_public=True)
            )
            org_stats = stats.copy()
            org_stats['org_new_items'] = org_items.count()
            
            # Find admin users to send report to
            admin_users = User.objects.filter(
                organization=org,
                is_staff=True
            )
            
            admin_emails = [user.email for user in admin_users if user.email]
            
            if not admin_emails:
                logger.info(f"No admin users with email addresses found for organization {org.name}")
                continue
            
            # Prepare the email context
            context = {
                'organization': org.name,
                'stats': org_stats,
                'report_period_start': report_period_start,
                'report_period_end': timezone.now(),
                'base_url': settings.BASE_URL if hasattr(settings, 'BASE_URL') else '/'
            }
            
            # Generate the email content
            subject = f"Weekly Threat Intelligence Report - {org.name}"
            text_message = render_to_string('vision/emails/threat_intel_report.txt', context)
            html_message = render_to_string('vision/emails/threat_intel_report.html', context)
            
            # Send the email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=admin_emails
            )
            email.attach_alternative(html_message, "text/html")
            email.send()
            
            logger.info(f"Sent threat intelligence report to {len(admin_emails)} admins for organization {org.name}")
            
        except Exception as e:
            logger.error(f"Error generating threat intel report for organization {org.name}: {str(e)}")
    
    return {
        'status': 'success',
        'organizations_processed': Organization.objects.count(),
        'total_new_items': stats['total_new_items']
    }


@shared_task
def auto_enrich_cases():
    """
    Automatically enrich cases with threat intelligence.
    
    This task:
    1. Finds cases that haven't been enriched with threat intelligence
    2. Processes observables in those cases
    3. Updates cases with any matching threat intelligence
    """
    # Find recent cases (created in the last 7 days)
    recent_time = timezone.now() - timedelta(days=7)
    
    # Using exclude instead of Q objects to avoid syntax errors
    recent_cases = Case.objects.filter(
        created_at__gte=recent_time
    ).exclude(
        timeline_events__event_type='threat_intel_urls'
    )
    
    cases_checked = 0
    cases_enriched = 0
    
    for case in recent_cases:
        try:
            # Skip cases without observables
            if not case.observables.exists():
                continue
            
            # Try to enrich the case
            stats = MISPCaseIntegration.enrich_case_with_threat_intel(case)
            cases_checked += 1
            
            if stats['observables_enriched'] > 0:
                cases_enriched += 1
                
                # Add a note about automatic enrichment
                case.add_timeline_event(
                    event_type='auto_enriched',
                    title=f"Case automatically enriched with threat intelligence",
                    description=f"System automatically enriched {stats['observables_enriched']} observables with threat intelligence."
                )
                
                logger.info(f"Automatically enriched case {case.id} with threat intelligence data")
            
        except Exception as e:
            logger.error(f"Error automatically enriching case {case.id}: {str(e)}")
    
    return {
        'status': 'success',
        'cases_checked': cases_checked,
        'cases_enriched': cases_enriched
    } 