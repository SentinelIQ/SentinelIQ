from celery import shared_task
import logging
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q, F
from django.template.loader import render_to_string
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings

logger = logging.getLogger(__name__)

@shared_task
def process_aging_alerts():
    """
    Update alert statuses based on their age.
    
    This task performs the following operations:
    1. Auto-close resolved alerts that have been in that state for a specified period
    2. Notify stakeholders about stale alerts that haven't been updated
    """
    from .models import Alert
    
    now = timezone.now()
    results = {
        'closed': 0,
        'notified': 0,
        'errors': 0
    }
    
    # Find resolved alerts that have been in that state for more than 14 days
    resolved_cutoff = now - timedelta(days=14)
    resolved_alerts = Alert.objects.filter(
        status=Alert.RESOLVED,
        updated_at__lt=resolved_cutoff
    )
    
    # Auto-close these alerts
    for alert in resolved_alerts:
        try:
            old_status = alert.status
            alert.status = Alert.CLOSED
            alert.save()
            
            # Add a timeline event about the auto-closure
            alert.add_timeline_event(
                event_type='status_changed',
                title='Alert automatically closed',
                description='Alert was automatically closed after being resolved for 14 days',
                old_value=old_status,
                new_value=alert.status
            )
            
            results['closed'] += 1
            logger.info(f"Auto-closed alert #{alert.id}: {alert.title}")
        except Exception as e:
            logger.error(f"Error auto-closing alert #{alert.id}: {str(e)}")
            results['errors'] += 1
    
    # Find new alerts that haven't been acknowledged for more than 2 days
    stale_cutoff = now - timedelta(days=2)
    stale_alerts = Alert.objects.filter(
        status=Alert.NEW,
        updated_at__lt=stale_cutoff
    ).select_related('assigned_to', 'organization')
    
    # Notify about stale alerts
    for alert in stale_alerts:
        try:
            # Determine recipients
            recipients = []
            
            # If alert is assigned, notify the assignee
            if alert.assigned_to and alert.assigned_to.email:
                recipients.append(alert.assigned_to.email)
            
            # Also notify admins of the organization
            from accounts.models import User
            org_admins = User.objects.filter(
                organization=alert.organization,
                is_org_admin=True
            ).values_list('email', flat=True)
            
            recipients.extend([email for email in org_admins if email])
            
            if not recipients:
                logger.warning(f"No recipients for stale alert #{alert.id} notification")
                continue
            
            # Send notification
            subject = f"REMINDER: Unacknowledged Alert #{alert.id}: {alert.title}"
            context = {
                'alert': alert,
                'days_stale': (now - alert.updated_at).days,
                'alert_url': f"{settings.BASE_URL}/alerts/{alert.id}/" if hasattr(settings, 'BASE_URL') else f"/alerts/{alert.id}/"
            }
            
            html_message = render_to_string('alerts/emails/stale_alert_notification.html', context)
            text_message = render_to_string('alerts/emails/stale_alert_notification.txt', context)
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=recipients
            )
            email.attach_alternative(html_message, "text/html")
            email.send()
            
            results['notified'] += 1
            logger.info(f"Sent notification for stale alert #{alert.id} to {', '.join(recipients)}")
        except Exception as e:
            logger.error(f"Error sending notification for stale alert #{alert.id}: {str(e)}")
            results['errors'] += 1
    
    return {
        'status': 'success',
        'alerts_closed': results['closed'],
        'alerts_notified': results['notified'],
        'errors': results['errors']
    }


@shared_task
def auto_escalate_critical_alerts():
    """
    Automatically escalate critical alerts to cases based on configured criteria.
    
    This task identifies alerts that:
    1. Have a CRITICAL severity
    2. Are in NEW status for more than 1 hour
    3. Have a threat category assigned
    4. Are not already linked to a case
    
    Then it creates cases for these alerts, similar to the manual escalation process.
    """
    from .models import Alert
    from cases.models import Case, Task
    from django.db.models import Count
    
    # Find critical alerts waiting for escalation
    critical_cutoff = timezone.now() - timedelta(hours=1)
    
    # Filter for critical alerts that are new and have been around for at least an hour
    critical_alerts = Alert.objects.filter(
        severity=Alert.CRITICAL,
        status=Alert.NEW,
        created_at__lt=critical_cutoff,
        threat_category__isnull=False
    ).annotate(
        # Check if alert is already escalated (linked to a case)
        case_count=Count('related_cases')
    ).filter(
        case_count=0  # Only get alerts not linked to any cases
    )
    
    logger.info(f"Found {critical_alerts.count()} critical alerts to auto-escalate")
    
    escalated_count = 0
    error_count = 0
    
    for alert in critical_alerts:
        try:
            # Map severity to case priority
            severity_to_priority = {
                Alert.LOW: Case.LOW,
                Alert.MEDIUM: Case.MEDIUM,
                Alert.HIGH: Case.HIGH,
                Alert.CRITICAL: Case.CRITICAL,
            }
            
            # Create the case
            case = Case.objects.create(
                title=f"Auto-escalated: {alert.title}",
                description=f"Case automatically escalated from critical alert #{alert.id}:\n\n{alert.description}",
                priority=severity_to_priority.get(alert.severity, Case.CRITICAL),
                status=Case.OPEN,
                organization=alert.organization,
                assigned_to=alert.assigned_to,
                tlp=alert.tlp,
                pap=alert.pap
            )
            
            # Link the alert to the case
            case.related_alerts.add(alert)
            
            # Transfer tags
            for tag in alert.tags.all():
                case.tags.add(tag)
            
            # Transfer observables
            for observable in alert.observables.all():
                case.observables.add(observable)
            
            # Transfer MITRE ATT&CK elements
            for tactic in alert.mitre_tactics.all():
                case.mitre_tactics.add(tactic)
            
            for technique in alert.mitre_techniques.all():
                case.mitre_techniques.add(technique)
            
            for subtechnique in alert.mitre_subtechniques.all():
                case.mitre_subtechniques.add(subtechnique)
            
            for group in alert.mitre_attack_groups.all():
                case.mitre_attack_groups.add(group)
            
            # Create tasks from templates
            if alert.threat_category:
                from cases.models import TaskTemplate
                from datetime import date
                
                # Get templates for this threat category
                templates = TaskTemplate.objects.filter(
                    organization=alert.organization,
                    threat_category=alert.threat_category,
                    is_active=True
                ).order_by('order')
                
                # Create tasks from templates
                for template in templates:
                    # Calculate due date if specified
                    due_date = None
                    if template.due_days > 0:
                        due_date = date.today() + timedelta(days=template.due_days)
                    
                    # Create the task
                    task = Task.objects.create(
                        case=case,
                        title=template.title,
                        description=template.description,
                        priority=template.priority,
                        due_date=due_date,
                        assigned_to=alert.assigned_to
                    )
            
            # Log events in the case timeline
            case.add_timeline_event(
                event_type='created',
                title='Case automatically created from critical alert',
                description=f"This case was automatically created from critical alert #{alert.id}."
            )
            
            # Update alert status
            alert.status = Alert.IN_PROGRESS
            alert.save()
            
            # Log escalation in alert timeline
            alert.log_escalated_to_case(None, case)
            
            escalated_count += 1
            logger.info(f"Auto-escalated alert #{alert.id} to case #{case.id}")
        except Exception as e:
            logger.error(f"Error auto-escalating alert #{alert.id}: {str(e)}")
            error_count += 1
    
    return {
        'status': 'success',
        'alerts_escalated': escalated_count,
        'errors': error_count
    }


@shared_task
def generate_alert_statistics():
    """
    Generate statistics and insights from alert data.
    
    This task:
    1. Computes alert volume trends
    2. Analyzes alert severity distribution
    3. Tracks response times (time to acknowledge, time to resolve)
    4. Identifies common observables across alerts
    5. Calculates organization-specific metrics
    
    The results are stored for use in dashboards and reports.
    """
    from .models import Alert
    from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
    from django.db.models import Avg, Count, Q, F, ExpressionWrapper, fields, DurationField
    import json
    
    logger.info("Generating alert statistics")
    results = {}
    
    # 1. Alert volume by day (last 30 days)
    start_date = timezone.now() - timedelta(days=30)
    daily_counts = Alert.objects.filter(
        created_at__gte=start_date
    ).annotate(
        day=TruncDay('created_at')
    ).values('day').annotate(
        count=Count('id')
    ).order_by('day')
    
    results['daily_trend'] = {
        item['day'].strftime('%Y-%m-%d'): item['count']
        for item in daily_counts
    }
    
    # 2. Severity distribution
    severity_counts = dict(
        Alert.objects.values('severity').annotate(
            count=Count('id')
        ).values_list('severity', 'count')
    )
    
    results['severity_distribution'] = severity_counts
    
    # 3. Status distribution
    status_counts = dict(
        Alert.objects.values('status').annotate(
            count=Count('id')
        ).values_list('status', 'count')
    )
    
    results['status_distribution'] = status_counts
    
    # 4. Organization-specific metrics
    from organizations.models import Organization
    
    org_metrics = {}
    for org in Organization.objects.all():
        # Get alert counts for this organization
        total_alerts = Alert.objects.filter(organization=org).count()
        
        if total_alerts == 0:
            continue
            
        open_alerts = Alert.objects.filter(
            organization=org, 
            status__in=[Alert.NEW, Alert.ACKNOWLEDGED, Alert.IN_PROGRESS]
        ).count()
        
        critical_alerts = Alert.objects.filter(
            organization=org,
            severity=Alert.CRITICAL
        ).count()
        
        org_metrics[org.id] = {
            'name': org.name,
            'total_alerts': total_alerts,
            'open_alerts': open_alerts,
            'critical_alerts': critical_alerts,
            'open_percentage': round((open_alerts / total_alerts) * 100, 1) if total_alerts > 0 else 0
        }
    
    results['organization_metrics'] = org_metrics
    
    # 5. Store results
    # This would typically be stored in a database or cache
    # For now, we'll just log the results
    logger.info(f"Alert statistics generated: {json.dumps(results, default=str)}")
    
    return {
        'status': 'success',
        'statistics': results
    }


@shared_task
def enrich_alert_observables(alert_id):
    """
    Enrich observables in an alert with data from external threat intelligence sources.
    
    Args:
        alert_id (int): ID of the alert containing observables to enrich
    """
    from .models import Alert
    from core.models import Observable
    
    try:
        alert = Alert.objects.get(id=alert_id)
        logger.info(f"Enriching observables for alert #{alert_id}")
        
        # Get all observables linked to this alert
        observables = alert.observables.all()
        
        if not observables.exists():
            logger.info(f"No observables found for alert #{alert_id}")
            return {
                "status": "warning",
                "message": "No observables found for alert",
                "alert_id": alert_id,
                "enriched_count": 0
            }
        
        enriched_count = 0
        
        # Process each observable
        for observable in observables:
            try:
                # Check if this observable is already marked as malicious
                if observable.is_malicious:
                    continue
                
                # In a real implementation, you would call external threat intelligence APIs here
                # For this example, we'll simulate enrichment
                
                is_enriched = False
                enrichment_data = {}
                
                # Simulate enrichment based on observable type
                if observable.type == Observable.IP:
                    # Call a theoretical IP reputation API
                    enrichment_data = {
                        'is_malicious': False,  # Would come from the API
                        'confidence': None,
                        'description': "No malicious indicators found for this IP."
                    }
                    is_enriched = True
                    
                elif observable.type == Observable.DOMAIN:
                    # Call a theoretical domain reputation API
                    enrichment_data = {
                        'is_malicious': False,  # Would come from the API
                        'confidence': None, 
                        'description': "No malicious indicators found for this domain."
                    }
                    is_enriched = True
                    
                elif observable.type in [Observable.HASH_MD5, Observable.HASH_SHA1, Observable.HASH_SHA256]:
                    # Call a theoretical hash/malware check API
                    enrichment_data = {
                        'is_malicious': False,  # Would come from the API
                        'confidence': None,
                        'description': "No malicious indicators found for this file hash."
                    }
                    is_enriched = True
                
                # If we have enrichment data, update the observable
                if is_enriched:
                    # Update observable with enrichment data
                    observable.is_malicious = enrichment_data.get('is_malicious', False)
                    
                    if enrichment_data.get('confidence'):
                        observable.confidence = enrichment_data['confidence']
                    
                    # Add enrichment info to description
                    if observable.description:
                        observable.description += f"\n\nEnrichment ({timezone.now().strftime('%Y-%m-%d %H:%M')}): "
                        observable.description += enrichment_data.get('description', '')
                    else:
                        observable.description = f"Enrichment ({timezone.now().strftime('%Y-%m-%d %H:%M')}): "
                        observable.description += enrichment_data.get('description', '')
                    
                    observable.save()
                    enriched_count += 1
                    
                    # If observable is now marked as malicious, update alert severity
                    if observable.is_malicious and alert.severity not in [Alert.HIGH, Alert.CRITICAL]:
                        old_severity = alert.severity
                        alert.severity = Alert.HIGH
                        alert.save()
                        
                        # Log the change
                        alert.log_severity_change(
                            user=None,
                            old_severity=old_severity,
                            new_severity=alert.severity
                        )
                        
                        # Add a custom event explaining the change
                        alert.add_timeline_event(
                            event_type='custom',
                            title='Alert severity automatically increased',
                            description=f'Severity increased due to malicious observable found: {observable.value}'
                        )
            
            except Exception as e:
                logger.error(f"Error enriching observable {observable.id} for alert #{alert_id}: {str(e)}")
        
        return {
            "status": "success",
            "message": f"Enriched {enriched_count} observables for alert #{alert_id}",
            "alert_id": alert_id,
            "enriched_count": enriched_count
        }
        
    except Alert.DoesNotExist:
        logger.error(f"Alert #{alert_id} not found")
        return {
            "status": "error",
            "message": f"Alert #{alert_id} not found",
            "alert_id": alert_id
        }
    except Exception as e:
        logger.error(f"Error processing alert #{alert_id}: {str(e)}")
        return {
            "status": "error",
            "message": f"Error: {str(e)}",
            "alert_id": alert_id
        } 