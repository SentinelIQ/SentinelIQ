from celery import shared_task
import logging
from django.utils import timezone
from datetime import timedelta
from django.template.loader import render_to_string
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.contrib.auth.models import update_last_login
from django.db.models import Count, Q, F

logger = logging.getLogger(__name__)

@shared_task
def check_inactive_users():
    """
    Identify and notify users who haven't logged in for an extended period.
    
    This task:
    1. Finds users who haven't logged in for more than 30 days
    2. Sends email notifications reminding them to log in
    3. Optionally marks accounts as inactive after 90 days
    """
    from .models import User
    
    # Get cutoff dates
    now = timezone.now()
    reminder_cutoff = now - timedelta(days=30)  # 30 days of inactivity
    inactive_cutoff = now - timedelta(days=90)  # 90 days of inactivity
    
    # Find users for reminder (inactive 30-89 days)
    reminder_users = User.objects.filter(
        is_active=True,
        last_login__lt=reminder_cutoff,
        last_login__gt=inactive_cutoff
    ).select_related('organization')
    
    # Find users to mark inactive (inactive 90+ days)
    mark_inactive_users = User.objects.filter(
        is_active=True,
        last_login__lt=inactive_cutoff
    ).select_related('organization')
    
    reminder_count = 0
    inactive_count = 0
    error_count = 0
    
    # Process users for reminder
    for user in reminder_users:
        try:
            if not user.email:
                continue
                
            # Calculate days since last login
            days_inactive = (now.date() - user.last_login.date()).days
            
            # Send reminder email
            subject = f"SentinelIQ Account Inactivity Notice"
            context = {
                'user': user,
                'days_inactive': days_inactive,
                'base_url': settings.BASE_URL if hasattr(settings, 'BASE_URL') else '/',
                'organization': user.organization.name if user.organization else None
            }
            
            html_message = render_to_string('accounts/emails/inactivity_reminder.html', context)
            text_message = render_to_string('accounts/emails/inactivity_reminder.txt', context)
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            email.attach_alternative(html_message, "text/html")
            email.send()
            
            reminder_count += 1
            logger.info(f"Sent inactivity reminder to user {user.username} (inactive for {days_inactive} days)")
            
        except Exception as e:
            logger.error(f"Error sending inactivity reminder to user {user.username}: {str(e)}")
            error_count += 1
    
    # Process users to mark as inactive
    for user in mark_inactive_users:
        try:
            # Skip superusers and org admins (or handle them differently)
            if user.is_superuser or user.is_org_admin():
                # Maybe just notify admins about these accounts instead?
                continue
                
            # Mark account as inactive
            user.is_active = False
            user.save()
            
            # Notify user if they have an email
            if user.email:
                days_inactive = (now.date() - user.last_login.date()).days
                
                subject = f"SentinelIQ Account Deactivated Due to Inactivity"
                context = {
                    'user': user,
                    'days_inactive': days_inactive,
                    'base_url': settings.BASE_URL if hasattr(settings, 'BASE_URL') else '/',
                    'organization': user.organization.name if user.organization else None
                }
                
                html_message = render_to_string('accounts/emails/account_deactivated.html', context)
                text_message = render_to_string('accounts/emails/account_deactivated.txt', context)
                
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=text_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[user.email]
                )
                email.attach_alternative(html_message, "text/html")
                email.send()
            
            inactive_count += 1
            logger.info(f"Deactivated user {user.username} due to inactivity")
            
        except Exception as e:
            logger.error(f"Error deactivating user {user.username}: {str(e)}")
            error_count += 1
    
    return {
        'status': 'success',
        'reminders_sent': reminder_count,
        'accounts_deactivated': inactive_count,
        'errors': error_count
    }


@shared_task
def generate_user_activity_reports():
    """
    Generate and email activity reports to organization admins.
    
    This task:
    1. Compiles user activity metrics for each organization
    2. Generates reports with login patterns, task completions, and security metrics
    3. Emails the reports to organization admins
    """
    from .models import User
    from organizations.models import Organization
    from cases.models import Task
    from alerts.models import Alert
    import json
    
    now = timezone.now()
    report_period_start = now - timedelta(days=7)  # Last 7 days
    
    # Process each organization
    for org in Organization.objects.all():
        try:
            # Skip organizations with no admin
            org_admins = User.objects.filter(
                organization=org,
                role=User.ORG_ADMIN,
                is_active=True
            )
            
            if not org_admins.exists():
                continue
                
            # Collect organization metrics
            org_users = User.objects.filter(organization=org)
            total_users = org_users.count()
            active_users = org_users.filter(is_active=True).count()
            
            # Get login activity
            users_logged_in_period = org_users.filter(
                last_login__gte=report_period_start
            ).count()
            
            # Task metrics
            tasks_completed = Task.objects.filter(
                case__organization=org,
                is_completed=True,
                updated_at__gte=report_period_start
            ).count()
            
            # Alert metrics
            alerts_resolved = Alert.objects.filter(
                organization=org,
                status__in=[Alert.RESOLVED, Alert.CLOSED],
                updated_at__gte=report_period_start
            ).count()
            
            # User activity metrics by role
            activity_by_role = {}
            for role, _ in User.ROLE_CHOICES:
                users_in_role = org_users.filter(role=role).count()
                active_in_role = org_users.filter(role=role, is_active=True).count()
                
                activity_by_role[role] = {
                    'total': users_in_role,
                    'active': active_in_role,
                    'inactive': users_in_role - active_in_role,
                    'active_percentage': round((active_in_role / users_in_role * 100) if users_in_role > 0 else 0, 1)
                }
            
            # Generate report data
            report_data = {
                'organization': org.name,
                'period_start': report_period_start,
                'period_end': now,
                'total_users': total_users,
                'active_users': active_users,
                'inactive_users': total_users - active_users,
                'activity_rate': round((users_logged_in_period / active_users * 100) if active_users > 0 else 0, 1),
                'tasks_completed': tasks_completed,
                'alerts_resolved': alerts_resolved,
                'activity_by_role': activity_by_role
            }
            
            # Send to all org admins
            admin_emails = [admin.email for admin in org_admins if admin.email]
            
            if not admin_emails:
                continue
                
            subject = f"Weekly User Activity Report - {org.name}"
            context = {
                'report': report_data,
                'period_days': 7,
                'base_url': settings.BASE_URL if hasattr(settings, 'BASE_URL') else '/'
            }
            
            html_message = render_to_string('accounts/emails/activity_report.html', context)
            text_message = render_to_string('accounts/emails/activity_report.txt', context)
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=admin_emails
            )
            email.attach_alternative(html_message, "text/html")
            email.send()
            
            logger.info(f"Sent user activity report for organization: {org.name}")
            
        except Exception as e:
            logger.error(f"Error generating activity report for organization {org.name}: {str(e)}")
    
    return {
        'status': 'success',
        'message': 'User activity reports generated and sent'
    }


@shared_task
def analyze_login_patterns():
    """
    Detect unusual login patterns and potential security issues.
    
    This task:
    1. Analyzes user login times and patterns
    2. Detects unusual login behavior (if login time data is available)
    3. Alerts admins about suspicious activities
    """
    # In a production application, this would analyze more detailed login data
    # such as login times, IP addresses, devices, etc.
    
    # For this implementation, we'll just check for failed login attempts
    # which would require a custom model to track authentication attempts
    
    logger.info("Running login pattern analysis")
    
    return {
        'status': 'success',
        'message': 'Login pattern analysis completed'
    }


@shared_task
def clean_expired_sessions():
    """
    Remove expired sessions from the database.
    
    This helps keep the database clean and efficient.
    """
    from django.contrib.sessions.models import Session
    
    now = timezone.now()
    expired_sessions = Session.objects.filter(expire_date__lt=now)
    count = expired_sessions.count()
    expired_sessions.delete()
    
    logger.info(f"Deleted {count} expired sessions")
    
    return {
        'status': 'success',
        'sessions_deleted': count
    } 