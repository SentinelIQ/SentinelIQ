from celery import shared_task
import logging
import traceback
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
import requests
import json

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_notification(self, notification_log_id):
    """Celery task to send an email notification"""
    from .models import NotificationLog
    
    try:
        notification_log = NotificationLog.objects.get(id=notification_log_id)
        destination = notification_log.destination
        config = destination.config
        
        # Get recipients from config
        recipients = config.get('recipients', [])
        if not recipients:
            notification_log.mark_as_failed("No recipients specified in destination config")
            return
        
        # Get sender email
        from_email = config.get('from_email', settings.DEFAULT_FROM_EMAIL)
        
        # Send email
        send_mail(
            notification_log.subject,
            notification_log.body,
            from_email,
            recipients,
            fail_silently=False,
            html_message=notification_log.body if config.get('use_html', False) else None
        )
        notification_log.mark_as_sent()
        logger.info(f"Email notification {notification_log_id} sent successfully")
    
    except NotificationLog.DoesNotExist:
        logger.error(f"Notification log {notification_log_id} does not exist")
    except Exception as e:
        error_msg = f"Failed to send email: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        
        try:
            notification_log.mark_as_failed(error_msg)
        except Exception:
            pass
        
        # Retry the task if not max retries reached
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for email notification {notification_log_id}")

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_webhook_notification(self, notification_log_id):
    """Celery task to send a webhook notification"""
    from .models import NotificationLog
    
    try:
        notification_log = NotificationLog.objects.get(id=notification_log_id)
        destination = notification_log.destination
        config = destination.config
        
        # Get webhook URL
        webhook_url = config.get('url')
        if not webhook_url:
            notification_log.mark_as_failed("No URL specified in destination config")
            return
        
        # Prepare headers and payload
        headers = config.get('headers', {})
        headers.setdefault('Content-Type', 'application/json')
        
        payload = {
            'subject': notification_log.subject,
            'body': notification_log.body,
            'event_data': notification_log.event_data,
            'tracking_id': str(notification_log.tracking_id),
            'timestamp': timezone.now().isoformat()
        }
        
        # Send webhook
        response = requests.post(
            webhook_url,
            json=payload,
            headers=headers,
            timeout=config.get('timeout', 10)
        )
        
        if response.status_code >= 200 and response.status_code < 300:
            notification_log.mark_as_sent()
            logger.info(f"Webhook notification {notification_log_id} sent successfully")
        else:
            error_msg = f"Webhook returned non-success status code: {response.status_code}, response: {response.text}"
            notification_log.mark_as_failed(error_msg)
            logger.error(error_msg)
            raise self.retry(exc=Exception(error_msg))
    
    except NotificationLog.DoesNotExist:
        logger.error(f"Notification log {notification_log_id} does not exist")
    except Exception as e:
        error_msg = f"Failed to send webhook: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        
        try:
            notification_log.mark_as_failed(error_msg)
        except Exception:
            pass
        
        # Retry the task if not max retries reached
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for webhook notification {notification_log_id}")

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_slack_notification(self, notification_log_id):
    """Celery task to send a Slack notification"""
    from .models import NotificationLog
    
    try:
        notification_log = NotificationLog.objects.get(id=notification_log_id)
        destination = notification_log.destination
        config = destination.config
        
        # Get webhook URL
        webhook_url = config.get('webhook_url')
        if not webhook_url:
            notification_log.mark_as_failed("No webhook URL specified in destination config")
            return
        
        # Prepare payload
        payload = {
            'text': notification_log.subject,
            'blocks': [
                {
                    'type': 'header',
                    'text': {
                        'type': 'plain_text',
                        'text': notification_log.subject
                    }
                },
                {
                    'type': 'section',
                    'text': {
                        'type': 'mrkdwn',
                        'text': notification_log.body
                    }
                },
                {
                    'type': 'context',
                    'elements': [
                        {
                            'type': 'mrkdwn',
                            'text': f"*Tracking ID:* {notification_log.tracking_id}"
                        }
                    ]
                }
            ]
        }
        
        # Add optional configuration
        if config.get('channel'):
            payload['channel'] = config['channel']
        if config.get('username'):
            payload['username'] = config['username']
        if config.get('icon_emoji'):
            payload['icon_emoji'] = config['icon_emoji']
        if config.get('icon_url'):
            payload['icon_url'] = config['icon_url']
        
        # Send to Slack
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=config.get('timeout', 10)
        )
        
        if response.status_code == 200 and response.text == 'ok':
            notification_log.mark_as_sent()
            logger.info(f"Slack notification {notification_log_id} sent successfully")
        else:
            error_msg = f"Slack webhook returned non-success response: {response.status_code}, response: {response.text}"
            notification_log.mark_as_failed(error_msg)
            logger.error(error_msg)
            raise self.retry(exc=Exception(error_msg))
    
    except NotificationLog.DoesNotExist:
        logger.error(f"Notification log {notification_log_id} does not exist")
    except Exception as e:
        error_msg = f"Failed to send Slack notification: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        
        try:
            notification_log.mark_as_failed(error_msg)
        except Exception:
            pass
        
        # Retry the task if not max retries reached
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for Slack notification {notification_log_id}")

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_mattermost_notification(self, notification_log_id):
    """Celery task to send a Mattermost notification"""
    from .models import NotificationLog
    
    try:
        notification_log = NotificationLog.objects.get(id=notification_log_id)
        destination = notification_log.destination
        config = destination.config
        
        # Get webhook URL
        webhook_url = config.get('webhook_url')
        if not webhook_url:
            notification_log.mark_as_failed("No webhook URL specified in destination config")
            return
        
        # Prepare payload
        payload = {
            'text': f"### {notification_log.subject}\n\n{notification_log.body}\n\n**Tracking ID:** {notification_log.tracking_id}"
        }
        
        # Add optional configuration
        if config.get('channel'):
            payload['channel'] = config['channel']
        if config.get('username'):
            payload['username'] = config['username']
        if config.get('icon_url'):
            payload['icon_url'] = config['icon_url']
        
        # Send to Mattermost
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=config.get('timeout', 10)
        )
        
        if response.status_code == 200:
            notification_log.mark_as_sent()
            logger.info(f"Mattermost notification {notification_log_id} sent successfully")
        else:
            error_msg = f"Mattermost webhook returned non-success response: {response.status_code}, response: {response.text}"
            notification_log.mark_as_failed(error_msg)
            logger.error(error_msg)
            raise self.retry(exc=Exception(error_msg))
    
    except NotificationLog.DoesNotExist:
        logger.error(f"Notification log {notification_log_id} does not exist")
    except Exception as e:
        error_msg = f"Failed to send Mattermost notification: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        
        try:
            notification_log.mark_as_failed(error_msg)
        except Exception:
            pass
        
        # Retry the task if not max retries reached
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for Mattermost notification {notification_log_id}")

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_custom_http_notification(self, notification_log_id):
    """Celery task to send a custom HTTP notification"""
    from .models import NotificationLog
    
    try:
        notification_log = NotificationLog.objects.get(id=notification_log_id)
        destination = notification_log.destination
        config = destination.config
        
        # Get URL and method
        url = config.get('url')
        method = config.get('method', 'POST').upper()
        
        if not url:
            notification_log.mark_as_failed("No URL specified in destination config")
            return
        
        # Prepare headers
        headers = config.get('headers', {})
        
        # Prepare payload
        if config.get('payload_format') == 'json':
            json_payload = config.get('payload_template', {}).copy()
            # Replace placeholders with actual values
            for key, value in json_payload.items():
                if isinstance(value, str):
                    if '{{subject}}' in value:
                        json_payload[key] = value.replace('{{subject}}', notification_log.subject)
                    if '{{body}}' in value:
                        json_payload[key] = value.replace('{{body}}', notification_log.body)
                    if '{{tracking_id}}' in value:
                        json_payload[key] = value.replace('{{tracking_id}}', str(notification_log.tracking_id))
            
            kwargs = {'json': json_payload}
        else:
            # Default to simple payload
            kwargs = {'json': {
                'subject': notification_log.subject,
                'body': notification_log.body,
                'event_data': notification_log.event_data,
                'tracking_id': str(notification_log.tracking_id),
                'timestamp': timezone.now().isoformat()
            }}
        
        # Add headers to kwargs
        kwargs['headers'] = headers
        
        # Add timeout
        kwargs['timeout'] = config.get('timeout', 10)
        
        # Make the request
        http_method = getattr(requests, method.lower(), requests.post)
        response = http_method(url, **kwargs)
        
        # Check response
        if response.status_code >= 200 and response.status_code < 300:
            notification_log.mark_as_sent()
            logger.info(f"Custom HTTP notification {notification_log_id} sent successfully")
        else:
            error_msg = f"Custom HTTP request returned non-success status code: {response.status_code}, response: {response.text}"
            notification_log.mark_as_failed(error_msg)
            logger.error(error_msg)
            raise self.retry(exc=Exception(error_msg))
    
    except NotificationLog.DoesNotExist:
        logger.error(f"Notification log {notification_log_id} does not exist")
    except Exception as e:
        error_msg = f"Failed to send custom HTTP notification: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        
        try:
            notification_log.mark_as_failed(error_msg)
        except Exception:
            pass
        
        # Retry the task if not max retries reached
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for custom HTTP notification {notification_log_id}")

@shared_task
def process_notification_event(event_id):
    """Process a notification event asynchronously"""
    from .models import NotificationEvent, NotificationRule, NotificationLog
    from .services import NotificationService
    
    try:
        event = NotificationEvent.objects.get(id=event_id, processed=False)
        
        # Find matching rules
        matching_rules = NotificationService._find_matching_rules(event)
        
        # Create notification logs
        logs = []
        for rule in matching_rules:
            for destination in rule.destinations.filter(is_active=True):
                # Format subject and body using template
                subject, body = NotificationService._format_templates(rule, event.event_data)
                
                # Create notification log
                log = NotificationLog.objects.create(
                    rule=rule,
                    destination=destination,
                    subject=subject,
                    body=body,
                    event_data=event.event_data,
                    status=NotificationLog.PENDING,
                    organization=event.organization
                )
                logs.append(log)
                
                # Queue the appropriate task based on destination type
                if destination.type == 'email':
                    send_email_notification.delay(log.id)
                elif destination.type == 'webhook':
                    send_webhook_notification.delay(log.id)
                elif destination.type == 'slack':
                    send_slack_notification.delay(log.id)
                elif destination.type == 'mattermost':
                    send_mattermost_notification.delay(log.id)
                elif destination.type == 'custom_http':
                    send_custom_http_notification.delay(log.id)
        
        # Mark event as processed
        event.processed = True
        event.save()
        
        logger.info(f"Processed notification event {event_id}, created {len(logs)} notification logs")
        return len(logs)
    
    except NotificationEvent.DoesNotExist:
        logger.error(f"Notification event {event_id} does not exist or already processed")
    except Exception as e:
        logger.error(f"Error processing notification event {event_id}: {str(e)}\n{traceback.format_exc()}")
        raise

@shared_task
def clean_old_notification_logs(days=30):
    """Delete notification logs older than the specified number of days"""
    from .models import NotificationLog
    from django.db.models import Q
    
    cutoff_date = timezone.now() - timezone.timedelta(days=days)
    
    # Delete logs, excluding failed logs that are recent (within 7 days)
    recent_cutoff = timezone.now() - timezone.timedelta(days=7)
    
    deleted_count = NotificationLog.objects.filter(
        Q(created_at__lt=cutoff_date) & 
        ~Q(status='failed', created_at__gt=recent_cutoff)
    ).delete()[0]
    
    logger.info(f"Deleted {deleted_count} notification logs older than {days} days")
    return deleted_count

@shared_task
def generate_notification_statistics():
    """Gerar estatísticas de notificações para o painel de controle"""
    from .models import NotificationLog, NotificationRule, NotificationDestination
    from django.db.models import Count, Q
    
    # Período de análise: últimos 7 dias
    cutoff_date = timezone.now() - timezone.timedelta(days=7)
    
    # Estatísticas por status
    status_stats = NotificationLog.objects.filter(
        created_at__gte=cutoff_date
    ).values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    # Estatísticas por tipo de destino
    destination_stats = NotificationLog.objects.filter(
        created_at__gte=cutoff_date
    ).values('destination__type').annotate(
        count=Count('id')
    ).order_by('destination__type')
    
    # Estatísticas por regra
    rule_stats = NotificationLog.objects.filter(
        created_at__gte=cutoff_date
    ).values('rule__name').annotate(
        count=Count('id')
    ).order_by('-count')[:10]  # Top 10 regras
    
    stats = {
        'period_start': cutoff_date.isoformat(),
        'period_end': timezone.now().isoformat(),
        'total_notifications': NotificationLog.objects.filter(created_at__gte=cutoff_date).count(),
        'status_distribution': list(status_stats),
        'destination_types': list(destination_stats),
        'top_rules': list(rule_stats),
    }
    
    logger.info(f"Generated notification statistics for past 7 days")
    return stats

@shared_task
def retry_failed_notifications(max_retries=3, hours=24):
    """Tentar novamente enviar notificações que falharam nas últimas X horas"""
    from .models import NotificationLog
    from .services import NotificationService
    
    cutoff_time = timezone.now() - timezone.timedelta(hours=hours)
    
    # Buscar notificações falhas recentes com menos de max_retries tentativas
    failed_logs = NotificationLog.objects.filter(
        status='failed',
        created_at__gte=cutoff_time,
        retry_count__lt=max_retries
    )
    
    retry_count = 0
    for log in failed_logs:
        try:
            # Incrementar contador de tentativas
            log.retry_count = (log.retry_count or 0) + 1
            log.status = 'pending'
            log.save(update_fields=['retry_count', 'status'])
            
            # Enviar novamente
            NotificationService.send_notification(log)
            retry_count += 1
        except Exception as e:
            error_msg = f"Retry failed: {str(e)}"
            logger.error(error_msg)
            log.mark_as_failed(error_msg)
    
    logger.info(f"Retried {retry_count} failed notifications")
    return retry_count

@shared_task
def monitor_notification_health():
    """Monitorar a saúde do sistema de notificações e alertar se houver problemas"""
    from .models import NotificationLog
    from django.core.mail import mail_admins
    
    # Verificar taxa de falha nas últimas 2 horas
    cutoff_time = timezone.now() - timezone.timedelta(hours=2)
    
    total_recent = NotificationLog.objects.filter(
        created_at__gte=cutoff_time
    ).count()
    
    if total_recent == 0:
        # Não houve notificações recentes, nada a monitorar
        return {
            'status': 'ok',
            'message': 'No recent notifications to analyze'
        }
    
    failed_recent = NotificationLog.objects.filter(
        created_at__gte=cutoff_time,
        status='failed'
    ).count()
    
    failure_rate = (failed_recent / total_recent) * 100
    
    result = {
        'status': 'ok',
        'total_notifications': total_recent,
        'failed_notifications': failed_recent,
        'failure_rate': failure_rate
    }
    
    # Alertar se a taxa de falha for alta (>20%)
    if failure_rate > 20:
        result['status'] = 'alert'
        result['message'] = f"High notification failure rate: {failure_rate:.1f}%"
        
        # Enviar alerta para os administradores
        subject = f"ALERTA: Alta taxa de falha em notificações ({failure_rate:.1f}%)"
        message = (
            f"O sistema detectou uma alta taxa de falha nas notificações:\n\n"
            f"- Total de notificações: {total_recent}\n"
            f"- Notificações falhas: {failed_recent}\n"
            f"- Taxa de falha: {failure_rate:.1f}%\n\n"
            f"Verifique o sistema e os logs para mais detalhes."
        )
        
        try:
            mail_admins(subject, message, fail_silently=True)
        except Exception as e:
            logger.error(f"Falha ao enviar alerta para administradores: {str(e)}")
    
    logger.info(f"Notification health check: {result['status']}")
    return result

@shared_task
def cleanup_notification_events(events_days=60, logs_days=90, keep_errors=True):
    """
    Limpar eventos e logs antigos de notificações para manter o banco de dados eficiente
    
    Args:
        events_days (int): Remover eventos mais antigos que este número de dias
        logs_days (int): Remover logs mais antigos que este número de dias
        keep_errors (bool): Se True, preserva logs com status de erro para investigação
    """
    from .models import NotificationEvent, NotificationLog
    from django.db.models import Q
    
    # Timestamp de corte para eventos
    events_cutoff = timezone.now() - timezone.timedelta(days=events_days)
    
    # Remover eventos antigos que já foram processados
    events_deleted, _ = NotificationEvent.objects.filter(
        created_at__lt=events_cutoff,
        processed=True
    ).delete()
    
    # Timestamp de corte para logs
    logs_cutoff = timezone.now() - timezone.timedelta(days=logs_days)
    
    # Construir query para logs antigos
    logs_query = NotificationLog.objects.filter(created_at__lt=logs_cutoff)
    
    # Se precisamos manter os erros, excluí-los da query
    if keep_errors:
        logs_query = logs_query.exclude(status='failed')
    
    # Remover logs antigos
    logs_deleted, _ = logs_query.delete()
    
    logger.info(f"Limpeza de notificações: removidos {events_deleted} eventos e {logs_deleted} logs antigos")
    
    return {
        'events_deleted': events_deleted,
        'logs_deleted': logs_deleted
    } 