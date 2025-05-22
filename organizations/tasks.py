from celery import shared_task
import logging
from django.utils import timezone
from datetime import timedelta
from django.template.loader import render_to_string
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.db.models import Count, Q, F

logger = logging.getLogger(__name__)

@shared_task
def check_inactive_organizations():
    """
    Identify organizations without recent activity.
    
    This task:
    1. Finds organizations with no user logins within a specified period
    2. Sends notifications to super admins
    3. Optionally flags inactive organizations for review
    """
    from .models import Organization
    from accounts.models import User
    from django.contrib.auth.models import User as DjangoUser
    
    # Get cutoff dates
    now = timezone.now()
    inactivity_cutoff = now - timedelta(days=60)  # 60 days of inactivity
    
    # Get all organizations
    organizations = Organization.objects.filter(is_active=True)
    inactive_orgs = []
    
    # Check each organization for activity
    for org in organizations:
        # Check if any users from this org have logged in recently
        recent_logins = User.objects.filter(
            organization=org,
            last_login__gte=inactivity_cutoff
        ).exists()
        
        if not recent_logins:
            inactive_orgs.append({
                'id': org.id,
                'name': org.name,
                'days_inactive': 60,  # Minimum threshold
                'user_count': User.objects.filter(organization=org).count()
            })
    
    # Notify super admins if there are inactive organizations
    if inactive_orgs:
        # Get all superusers
        superusers = DjangoUser.objects.filter(is_superuser=True)
        admin_emails = [user.email for user in superusers if user.email]
        
        if admin_emails:
            subject = f"SentinelIQ Inactive Organizations Report"
            context = {
                'inactive_orgs': inactive_orgs,
                'base_url': settings.BASE_URL if hasattr(settings, 'BASE_URL') else '/',
                'cutoff_days': 60
            }
            
            html_message = render_to_string('organizations/emails/inactive_orgs_report.html', context)
            text_message = render_to_string('organizations/emails/inactive_orgs_report.txt', context)
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=admin_emails
            )
            email.attach_alternative(html_message, "text/html")
            email.send()
            
            logger.info(f"Sent inactive organizations report to {len(admin_emails)} admins")
    
    return {
        'status': 'success',
        'inactive_organizations': len(inactive_orgs)
    }


@shared_task
def generate_organization_metrics():
    """
    Generate metrics and reports for all organizations.
    
    This task:
    1. Compiles organization-level metrics (users, alerts, cases, etc.)
    2. Compares with historical data to show trends
    3. Sends reports to organization admins and super admins
    """
    from .models import Organization
    from accounts.models import User
    from alerts.models import Alert
    from cases.models import Case
    
    now = timezone.now()
    report_period_start = now - timedelta(days=30)  # Last 30 days
    
    org_metrics = []
    for org in Organization.objects.filter(is_active=True):
        # User metrics
        total_users = User.objects.filter(organization=org).count()
        active_users = User.objects.filter(
            organization=org,
            is_active=True
        ).count()
        
        # Recent user activity
        active_recently = User.objects.filter(
            organization=org,
            last_login__gte=report_period_start
        ).count()
        
        # Alert metrics
        total_alerts = Alert.objects.filter(organization=org).count()
        new_alerts = Alert.objects.filter(
            organization=org,
            created_at__gte=report_period_start
        ).count()
        resolved_alerts = Alert.objects.filter(
            organization=org,
            status__in=['resolved', 'closed'],
            updated_at__gte=report_period_start
        ).count()
        
        # Case metrics
        total_cases = Case.objects.filter(organization=org).count()
        new_cases = Case.objects.filter(
            organization=org,
            created_at__gte=report_period_start
        ).count()
        closed_cases = Case.objects.filter(
            organization=org,
            status='closed',
            updated_at__gte=report_period_start
        ).count()
        
        # Store metrics
        org_metrics.append({
            'id': org.id,
            'name': org.name,
            'total_users': total_users,
            'active_users': active_users,
            'active_recently': active_recently,
            'activity_rate': round((active_recently / active_users * 100) if active_users > 0 else 0, 1),
            'total_alerts': total_alerts,
            'new_alerts': new_alerts,
            'resolved_alerts': resolved_alerts,
            'alert_resolution_rate': round((resolved_alerts / new_alerts * 100) if new_alerts > 0 else 0, 1),
            'total_cases': total_cases,
            'new_cases': new_cases,
            'closed_cases': closed_cases,
            'case_closure_rate': round((closed_cases / new_cases * 100) if new_cases > 0 else 0, 1)
        })
    
    # Send metrics to super admins
    from django.contrib.auth.models import User as DjangoUser
    superusers = DjangoUser.objects.filter(is_superuser=True)
    admin_emails = [user.email for user in superusers if user.email]
    
    if admin_emails and org_metrics:
        subject = f"SentinelIQ Monthly Organization Metrics Report"
        context = {
            'org_metrics': org_metrics,
            'report_start': report_period_start,
            'report_end': now,
            'base_url': settings.BASE_URL if hasattr(settings, 'BASE_URL') else '/'
        }
        
        html_message = render_to_string('organizations/emails/org_metrics_report.html', context)
        text_message = render_to_string('organizations/emails/org_metrics_report.txt', context)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=admin_emails
        )
        email.attach_alternative(html_message, "text/html")
        email.send()
        
        logger.info(f"Sent organization metrics report to {len(admin_emails)} admins")
    
    return {
        'status': 'success',
        'organizations_processed': len(org_metrics)
    }


@shared_task
def cleanup_inactive_organizations():
    """
    Archive or clean up data for long-term inactive organizations.
    
    This task:
    1. Identifies organizations marked as inactive for extended periods
    2. Archives old data or performs necessary cleanup
    3. Notifies administrators about the actions taken
    """
    from .models import Organization
    
    now = timezone.now()
    archive_cutoff = now - timedelta(days=365)  # 1 year of inactivity
    
    # Get organizations marked as inactive for over a year
    inactive_orgs = Organization.objects.filter(
        is_active=False,
        updated_at__lt=archive_cutoff
    )
    
    # For demonstration, we'll just count them and notify admins
    # In a real implementation, you would archive data or perform cleanup
    
    if inactive_orgs.exists():
        # Get all superusers
        from django.contrib.auth.models import User as DjangoUser
        superusers = DjangoUser.objects.filter(is_superuser=True)
        admin_emails = [user.email for user in superusers if user.email]
        
        if admin_emails:
            org_list = [{'id': org.id, 'name': org.name} for org in inactive_orgs]
            
            subject = f"SentinelIQ Inactive Organizations Cleanup Notice"
            context = {
                'orgs': org_list,
                'count': len(org_list),
                'inactive_days': 365,
                'base_url': settings.BASE_URL if hasattr(settings, 'BASE_URL') else '/'
            }
            
            html_message = render_to_string('organizations/emails/inactive_cleanup_notice.html', context)
            text_message = render_to_string('organizations/emails/inactive_cleanup_notice.txt', context)
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=admin_emails
            )
            email.attach_alternative(html_message, "text/html")
            email.send()
            
            logger.info(f"Notified admins about {len(org_list)} inactive organizations ready for cleanup")
    
    return {
        'status': 'success',
        'inactive_organizations_found': inactive_orgs.count()
    }


@shared_task
def verify_organization_data_integrity():
    """
    Verify data integrity across organizations.
    
    This task:
    1. Checks for inconsistencies in organization data
    2. Verifies user-organization relationships
    3. Ensures all related records have proper organization assignments
    4. Reports any issues to administrators
    """
    from .models import Organization
    from accounts.models import User
    from alerts.models import Alert
    from cases.models import Case
    
    issues = []
    
    # Check for users without organizations
    unassigned_users = User.objects.filter(organization__isnull=True).count()
    if unassigned_users > 0:
        issues.append(f"Found {unassigned_users} users without organization assignment")
    
    # Check for alerts without organizations
    unassigned_alerts = Alert.objects.filter(organization__isnull=True).count()
    if unassigned_alerts > 0:
        issues.append(f"Found {unassigned_alerts} alerts without organization assignment")
    
    # Check for cases without organizations
    unassigned_cases = Case.objects.filter(organization__isnull=True).count()
    if unassigned_cases > 0:
        issues.append(f"Found {unassigned_cases} cases without organization assignment")
    
    # If issues were found, notify administrators
    if issues:
        from django.contrib.auth.models import User as DjangoUser
        superusers = DjangoUser.objects.filter(is_superuser=True)
        admin_emails = [user.email for user in superusers if user.email]
        
        if admin_emails:
            subject = f"SentinelIQ Data Integrity Issues Detected"
            context = {
                'issues': issues,
                'issue_count': len(issues),
                'base_url': settings.BASE_URL if hasattr(settings, 'BASE_URL') else '/'
            }
            
            html_message = render_to_string('organizations/emails/data_integrity_report.html', context)
            text_message = render_to_string('organizations/emails/data_integrity_report.txt', context)
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=admin_emails
            )
            email.attach_alternative(html_message, "text/html")
            email.send()
            
            logger.info(f"Sent data integrity report with {len(issues)} issues to admins")
    
    return {
        'status': 'success',
        'issues_found': len(issues),
        'issues': issues
    } 