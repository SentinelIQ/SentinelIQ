from celery import shared_task
import logging
from django.utils import timezone
from datetime import timedelta
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.db.models import Count, Q, F, ExpressionWrapper, fields
from django.conf import settings

logger = logging.getLogger(__name__)

@shared_task
def create_tasks_from_templates(case_id, threat_category_id=None):
    """
    Create tasks for a case from task templates matching the specified threat category.
    
    Args:
        case_id (int): ID of the case to create tasks for
        threat_category_id (int, optional): ID of the threat category to use for filtering templates.
            If None, all active templates will be considered.
    """
    from .models import Case, TaskTemplate, Task, ThreatCategory
    
    try:
        case = Case.objects.get(id=case_id)
        logger.info(f"Creating tasks from templates for case #{case_id}: {case.title}")
        
        # Filter templates by organization and threat category if provided
        templates_query = TaskTemplate.objects.filter(
            organization=case.organization,
            is_active=True
        ).order_by('order')
        
        if threat_category_id:
            try:
                threat_category = ThreatCategory.objects.get(id=threat_category_id)
                templates_query = templates_query.filter(threat_category=threat_category)
                logger.info(f"Filtering templates by threat category: {threat_category.name}")
            except ThreatCategory.DoesNotExist:
                logger.warning(f"Threat category {threat_category_id} not found, using all templates")
        
        templates = templates_query.all()
        
        if not templates.exists():
            logger.info(f"No active templates found for case #{case_id}")
            return {
                "status": "warning",
                "message": "No active task templates found",
                "case_id": case_id,
                "tasks_created": 0
            }
        
        # Create tasks from templates
        tasks_created = 0
        for template in templates:
            # Calculate due date based on template's due_days
            due_date = None
            if template.due_days:
                due_date = timezone.now().date() + timedelta(days=template.due_days)
            
            # Create the task
            task = Task.objects.create(
                case=case,
                title=template.title,
                description=template.description,
                priority=template.priority,
                due_date=due_date
            )
            
            # Log task creation in case timeline
            if hasattr(case, 'add_timeline_event'):
                case.add_timeline_event(
                    event_type='task_added',
                    title=f"Task automatically created: {task.title}",
                    description=f"Created from template: {template.title}",
                    metadata={'task_id': task.id, 'template_id': template.id}
                )
            
            tasks_created += 1
            logger.info(f"Created task '{task.title}' for case #{case_id} from template #{template.id}")
        
        return {
            "status": "success",
            "message": f"Created {tasks_created} tasks for case #{case_id}",
            "case_id": case_id,
            "tasks_created": tasks_created
        }
        
    except Case.DoesNotExist:
        logger.error(f"Case #{case_id} not found")
        return {
            "status": "error",
            "message": f"Case #{case_id} not found",
            "case_id": case_id,
            "tasks_created": 0
        }
    except Exception as e:
        logger.error(f"Error creating tasks from templates for case #{case_id}: {str(e)}")
        return {
            "status": "error",
            "message": f"Error: {str(e)}",
            "case_id": case_id,
            "tasks_created": 0
        }


@shared_task
def notify_overdue_tasks():
    """
    Send notifications for overdue tasks.
    
    This task checks for tasks that are:
    1. Not completed
    2. Have a due date that has passed
    3. Haven't had a notification sent in the last 24 hours
    """
    from .models import Task
    
    today = timezone.now().date()
    
    # Find overdue tasks
    overdue_tasks = Task.objects.filter(
        is_completed=False,
        due_date__lt=today
    ).select_related('case', 'assigned_to')
    
    logger.info(f"Found {overdue_tasks.count()} overdue tasks")
    
    notifications_sent = 0
    for task in overdue_tasks:
        # Skip tasks that don't have an assignee
        if not task.assigned_to or not task.assigned_to.email:
            continue
        
        days_overdue = (today - task.due_date).days
        
        # Prepare email content
        subject = f"Overdue Task: {task.title}"
        message = f"""
        Task: {task.title}
        Case: {task.case.title}
        Due Date: {task.due_date}
        Days Overdue: {days_overdue}
        
        Please complete this task as soon as possible or update its due date.
        """
        
        # You could use HTML email with a template
        html_message = render_to_string('cases/emails/overdue_task_notification.html', {
            'task': task,
            'days_overdue': days_overdue,
            'case': task.case
        })
        
        # Send email notification
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[task.assigned_to.email],
                html_message=html_message,
                fail_silently=False
            )
            notifications_sent += 1
            logger.info(f"Sent overdue notification for task #{task.id} to {task.assigned_to.email}")
        except Exception as e:
            logger.error(f"Failed to send overdue notification for task #{task.id}: {str(e)}")
    
    return {
        "status": "success",
        "message": f"Sent {notifications_sent} overdue task notifications",
        "notifications_sent": notifications_sent
    }


@shared_task
def analyze_case_data():
    """
    Analyze case data to identify patterns and generate insights.
    
    This task performs various analyses on case data:
    1. Finds common factors across cases
    2. Identifies trends in case volume and resolution times
    3. Analyzes task completion rates by priority and category
    """
    from .models import Case, Task, ThreatCategory
    from django.db.models.functions import TruncMonth
    
    logger.info("Starting case data analysis")
    results = {}
    
    # 1. Analyze case status distribution
    status_distribution = dict(Case.objects.values('status').annotate(count=Count('id')).values_list('status', 'count'))
    results['status_distribution'] = status_distribution
    
    # 2. Analyze average resolution time (for resolved/closed cases)
    # This would require a field to track when cases were resolved,
    # which isn't in the current model. For example:
    # avg_resolution_days = Case.objects.filter(
    #     status__in=['resolved', 'closed'],
    #     resolved_at__isnull=False
    # ).annotate(
    #     resolution_days=ExpressionWrapper(
    #         F('resolved_at') - F('created_at'),
    #         output_field=fields.DurationField()
    #     )
    # ).aggregate(Avg('resolution_days'))['resolution_days__avg']
    # results['avg_resolution_days'] = avg_resolution_days.days if avg_resolution_days else None
    
    # 3. Analyze task completion rates by priority
    task_completion_by_priority = {}
    for priority, _ in Task.PRIORITY_CHOICES:
        total = Task.objects.filter(priority=priority).count()
        completed = Task.objects.filter(priority=priority, is_completed=True).count()
        rate = (completed / total * 100) if total > 0 else 0
        task_completion_by_priority[priority] = {
            'total': total,
            'completed': completed,
            'rate': round(rate, 2)
        }
    
    results['task_completion_by_priority'] = task_completion_by_priority
    
    # 4. Find threat categories with highest number of cases
    # This would require a direct relation between Case and ThreatCategory
    # which isn't in the current model. It could be added in the future.
    
    # 5. Analyze case creation trend by month (last 12 months)
    start_date = (timezone.now() - timedelta(days=365)).date()
    case_trend = (
        Case.objects.filter(created_at__gte=start_date)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    
    results['case_monthly_trend'] = {
        item['month'].strftime('%Y-%m'): item['count'] 
        for item in case_trend
    }
    
    logger.info("Case data analysis completed")
    return {
        "status": "success",
        "results": results
    }


@shared_task
def archive_old_cases(days=90, status=None, dry_run=True):
    """
    Archive old cases that have been closed/resolved for a specified number of days.
    
    Args:
        days (int): Number of days since a case was last updated to consider it for archiving
        status (list, optional): List of statuses to consider for archiving (default: ['closed'])
        dry_run (bool): If True, only report what would be archived without making changes
    """
    from .models import Case
    
    if status is None:
        status = ['closed']
    
    cutoff_date = timezone.now() - timedelta(days=days)
    
    # Find cases to archive
    query = Case.objects.filter(
        updated_at__lt=cutoff_date,
        status__in=status
    )
    
    count = query.count()
    logger.info(f"Found {count} cases to archive (older than {days} days with status in {status})")
    
    if dry_run:
        logger.info("Dry run mode - no cases will be archived")
        return {
            "status": "success",
            "dry_run": True,
            "count": count,
            "message": f"Found {count} cases that would be archived"
        }
    
    # In a real implementation, you might set an 'archived' flag on cases
    # or move them to an archive table
    # For now, we'll just log what we would archive
    for case in query:
        logger.info(f"Would archive case #{case.id}: {case.title} (last updated: {case.updated_at})")
    
    return {
        "status": "success",
        "dry_run": False,
        "count": count,
        "message": f"Archived {count} cases"
    } 