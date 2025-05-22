from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, FormView, TemplateView
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, Count, F, Case, When, Value, IntegerField, Sum
from django.http import JsonResponse, HttpResponseRedirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json

from accounts.views import OrgAdminRequiredMixin
from .models import NotificationDestination, NotificationRule, NotificationLog, NotificationEvent
from .forms import NotificationDestinationForm, NotificationRuleForm
from .services import NotificationService
from .tasks import generate_notification_statistics


# ===== Notification Destination Views =====

class NotificationDestinationListView(LoginRequiredMixin, ListView):
    """List view for notification destinations"""
    model = NotificationDestination
    template_name = 'notifications/destination_list.html'
    context_object_name = 'destinations'
    paginate_by = 10
    
    def get_queryset(self):
        """Filter destinations by organization"""
        queryset = NotificationDestination.objects.filter(
            organization=self.request.user.organization
        )
        
        # Apply search filter if provided
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(type__icontains=search)
            )
        
        # Apply type filter if provided
        dest_type = self.request.GET.get('type')
        if dest_type:
            queryset = queryset.filter(type=dest_type)
        
        # Apply status filter if provided
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['selected_type'] = self.request.GET.get('type', '')
        context['selected_status'] = self.request.GET.get('status', '')
        context['destination_types'] = NotificationDestination.TYPE_CHOICES
        return context


class NotificationDestinationDetailView(LoginRequiredMixin, DetailView):
    """Detail view for notification destinations"""
    model = NotificationDestination
    template_name = 'notifications/destination_detail.html'
    context_object_name = 'destination'
    
    def get_queryset(self):
        """Filter destinations by organization"""
        return NotificationDestination.objects.filter(
            organization=self.request.user.organization
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get recent logs for this destination
        context['logs'] = NotificationLog.objects.filter(
            destination=self.object
        ).order_by('-created_at')[:10]
        
        # Get rules that use this destination
        context['rules'] = self.object.rules.all()
        
        return context


class NotificationDestinationCreateView(LoginRequiredMixin, OrgAdminRequiredMixin, CreateView):
    """Create view for notification destinations"""
    model = NotificationDestination
    form_class = NotificationDestinationForm
    template_name = 'notifications/destination_form.html'
    success_url = reverse_lazy('notifications:destination_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization'] = self.request.user.organization
        return kwargs
    
    def form_valid(self, form):
        """Set organization and display success message"""
        form.instance.organization = self.request.user.organization
        messages.success(self.request, _('Notification destination created successfully.'))
        return super().form_valid(form)


class NotificationDestinationUpdateView(LoginRequiredMixin, OrgAdminRequiredMixin, UpdateView):
    """Update view for notification destinations"""
    model = NotificationDestination
    form_class = NotificationDestinationForm
    template_name = 'notifications/destination_form.html'
    
    def get_queryset(self):
        """Filter destinations by organization"""
        return NotificationDestination.objects.filter(
            organization=self.request.user.organization
        )
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization'] = self.request.user.organization
        return kwargs
    
    def form_valid(self, form):
        """Display success message"""
        messages.success(self.request, _('Notification destination updated successfully.'))
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('notifications:destination_detail', kwargs={'pk': self.object.pk})


class NotificationDestinationDeleteView(LoginRequiredMixin, OrgAdminRequiredMixin, DeleteView):
    """Delete view for notification destinations"""
    model = NotificationDestination
    template_name = 'notifications/destination_confirm_delete.html'
    success_url = reverse_lazy('notifications:destination_list')
    
    def get_queryset(self):
        """Filter destinations by organization"""
        return NotificationDestination.objects.filter(
            organization=self.request.user.organization
        )
    
    def delete(self, request, *args, **kwargs):
        """Display success message"""
        destination = self.get_object()
        messages.success(request, _(f'Notification destination "{destination.name}" deleted successfully.'))
        return super().delete(request, *args, **kwargs)


@login_required
def test_notification_destination(request, pk):
    """Test a notification destination by sending a test message"""
    destination = get_object_or_404(
        NotificationDestination,
        pk=pk,
        organization=request.user.organization
    )
    
    if request.method == 'POST':
        try:
            # Create a test notification log
            notification_log = NotificationLog.objects.create(
                rule=None,  # No rule for test notifications
                destination=destination,
                subject='Test Notification',
                body='This is a test notification from SentinelIQ.',
                event_data={'test': True, 'timestamp': timezone.now().isoformat()},
                status=NotificationLog.PENDING,
                organization=request.user.organization
            )
            
            # Send the test notification
            NotificationService.send_notification(notification_log)
            
            # Check the result
            if notification_log.status == NotificationLog.SUCCESS:
                messages.success(request, _('Test notification sent successfully.'))
            else:
                messages.error(request, _(f'Test notification failed: {notification_log.error_message}'))
            
            return redirect('notifications:destination_detail', pk=destination.pk)
        
        except Exception as e:
            messages.error(request, _(f'Error sending test notification: {str(e)}'))
            return redirect('notifications:destination_detail', pk=destination.pk)
    
    return render(request, 'notifications/destination_test.html', {
        'destination': destination
    })


# ===== Notification Rule Views =====

class NotificationRuleListView(LoginRequiredMixin, ListView):
    """List view for notification rules"""
    model = NotificationRule
    template_name = 'notifications/rule_list.html'
    context_object_name = 'rules'
    paginate_by = 10
    
    def get_queryset(self):
        """Filter rules by organization"""
        queryset = NotificationRule.objects.filter(
            organization=self.request.user.organization
        )
        
        # Apply search filter if provided
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )
        
        # Apply source filter if provided
        source = self.request.GET.get('source')
        if source:
            queryset = queryset.filter(source=source)
        
        # Apply event type filter if provided
        event_type = self.request.GET.get('event_type')
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        
        # Apply status filter if provided
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['selected_source'] = self.request.GET.get('source', '')
        context['selected_event_type'] = self.request.GET.get('event_type', '')
        context['selected_status'] = self.request.GET.get('status', '')
        context['source_choices'] = NotificationRule.SOURCE_CHOICES
        context['event_choices'] = NotificationRule.EVENT_CHOICES
        return context


class NotificationRuleDetailView(LoginRequiredMixin, DetailView):
    """Detail view for notification rules"""
    model = NotificationRule
    template_name = 'notifications/rule_detail.html'
    context_object_name = 'rule'
    
    def get_queryset(self):
        """Filter rules by organization"""
        return NotificationRule.objects.filter(
            organization=self.request.user.organization
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get recent logs for this rule
        context['logs'] = NotificationLog.objects.filter(
            rule=self.object
        ).order_by('-created_at')[:10]
        
        # Pretty format the conditions JSON
        if self.object.conditions:
            context['conditions_json'] = json.dumps(self.object.conditions, indent=2)
        else:
            context['conditions_json'] = '{}'
        
        return context


class NotificationRuleCreateView(LoginRequiredMixin, OrgAdminRequiredMixin, CreateView):
    """Create view for notification rules"""
    model = NotificationRule
    form_class = NotificationRuleForm
    template_name = 'notifications/rule_form.html'
    success_url = reverse_lazy('notifications:rule_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization'] = self.request.user.organization
        return kwargs
    
    def form_valid(self, form):
        """Set organization and display success message"""
        form.instance.organization = self.request.user.organization
        messages.success(self.request, _('Notification rule created successfully.'))
        return super().form_valid(form)


class NotificationRuleUpdateView(LoginRequiredMixin, OrgAdminRequiredMixin, UpdateView):
    """Update view for notification rules"""
    model = NotificationRule
    form_class = NotificationRuleForm
    template_name = 'notifications/rule_form.html'
    
    def get_queryset(self):
        """Filter rules by organization"""
        return NotificationRule.objects.filter(
            organization=self.request.user.organization
        )
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization'] = self.request.user.organization
        return kwargs
    
    def form_valid(self, form):
        """Display success message"""
        messages.success(self.request, _('Notification rule updated successfully.'))
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('notifications:rule_detail', kwargs={'pk': self.object.pk})


class NotificationRuleDeleteView(LoginRequiredMixin, OrgAdminRequiredMixin, DeleteView):
    """Delete view for notification rules"""
    model = NotificationRule
    template_name = 'notifications/rule_confirm_delete.html'
    success_url = reverse_lazy('notifications:rule_list')
    
    def get_queryset(self):
        """Filter rules by organization"""
        return NotificationRule.objects.filter(
            organization=self.request.user.organization
        )
    
    def delete(self, request, *args, **kwargs):
        """Display success message"""
        rule = self.get_object()
        messages.success(request, _(f'Notification rule "{rule.name}" deleted successfully.'))
        return super().delete(request, *args, **kwargs)


# ===== Notification Log Views =====

class NotificationLogListView(LoginRequiredMixin, ListView):
    """List view for notification logs"""
    model = NotificationLog
    template_name = 'notifications/log_list.html'
    context_object_name = 'logs'
    paginate_by = 20
    
    def get_queryset(self):
        """Filter logs by organization"""
        queryset = NotificationLog.objects.filter(
            organization=self.request.user.organization
        )
        
        # Apply status filter if provided
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Apply date range filter if provided
        start_date = self.request.GET.get('start_date')
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        
        end_date = self.request.GET.get('end_date')
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        # Apply destination filter if provided
        destination = self.request.GET.get('destination')
        if destination:
            queryset = queryset.filter(destination_id=destination)
        
        # Apply rule filter if provided
        rule = self.request.GET.get('rule')
        if rule:
            queryset = queryset.filter(rule_id=rule)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter values to context
        context['selected_status'] = self.request.GET.get('status', '')
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        context['selected_destination'] = self.request.GET.get('destination', '')
        context['selected_rule'] = self.request.GET.get('rule', '')
        
        # Add choices for filters
        context['status_choices'] = NotificationLog.STATUS_CHOICES
        context['destinations'] = NotificationDestination.objects.filter(
            organization=self.request.user.organization
        )
        context['rules'] = NotificationRule.objects.filter(
            organization=self.request.user.organization
        )
        
        return context


class NotificationLogDetailView(LoginRequiredMixin, DetailView):
    """Detail view for notification logs"""
    model = NotificationLog
    template_name = 'notifications/log_detail.html'
    context_object_name = 'log'
    
    def get_queryset(self):
        """Filter logs by organization"""
        return NotificationLog.objects.filter(
            organization=self.request.user.organization
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Pretty format the event data JSON
        if self.object.event_data:
            context['event_data_json'] = json.dumps(self.object.event_data, indent=2)
        else:
            context['event_data_json'] = '{}'
        
        return context


@login_required
def retry_notification(request, pk):
    """Retry sending a failed notification"""
    notification_log = get_object_or_404(
        NotificationLog,
        pk=pk,
        organization=request.user.organization
    )
    
    if request.method == 'POST':
        try:
            # Only retry failed notifications
            if notification_log.status == NotificationLog.FAILED:
                # Reset the status to pending
                notification_log.status = NotificationLog.PENDING
                notification_log.error_message = ''
                notification_log.save()
                
                # Send the notification
                NotificationService.send_notification(notification_log)
                
                # Check the result
                if notification_log.status == NotificationLog.SUCCESS:
                    messages.success(request, _('Notification sent successfully.'))
                else:
                    messages.error(request, _(f'Notification failed: {notification_log.error_message}'))
            else:
                messages.warning(request, _('Only failed notifications can be retried.'))
            
            return redirect('notifications:log_detail', pk=notification_log.pk)
        
        except Exception as e:
            messages.error(request, _(f'Error retrying notification: {str(e)}'))
            return redirect('notifications:log_detail', pk=notification_log.pk)
    
    return render(request, 'notifications/log_retry.html', {
        'log': notification_log
    })


# ===== Webhook Endpoint =====

@csrf_exempt
@require_POST
def webhook_receiver(request, token):
    """
    Receive webhook notifications from external sources
    
    This endpoint allows external systems to trigger notifications
    in the SentinelIQ system by sending webhook requests.
    """
    # Verify the token
    # In a real application, you would validate this token against a stored value
    if not token or len(token) < 32:
        return JsonResponse({'error': 'Invalid token'}, status=403)
    
    try:
        # Parse the incoming JSON data
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ['source_type', 'event_type', 'source_id', 'organization_id']
        for field in required_fields:
            if field not in data:
                return JsonResponse({'error': f'Missing required field: {field}'}, status=400)
        
        # Get the organization
        from organizations.models import Organization
        try:
            organization = Organization.objects.get(id=data['organization_id'])
        except Organization.DoesNotExist:
            return JsonResponse({'error': 'Organization not found'}, status=404)
        
        # Process the notification event
        NotificationService.process_event(
            event_type=data['event_type'],
            source_type=data['source_type'],
            source_id=data['source_id'],
            data=data.get('data', {}),
            organization=organization
        )
        
        return JsonResponse({'status': 'success'}, status=200)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ===== Dashboard =====

class NotificationDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard view with notification statistics"""
    template_name = 'notifications/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Generate basic statistics
        now = timezone.now()
        week_ago = now - timezone.timedelta(days=7)
        
        # Get logs from the last 7 days
        recent_logs = NotificationLog.objects.filter(
            organization=self.request.user.organization,
            created_at__gte=week_ago
        )
        
        total_count = recent_logs.count()
        successful_count = recent_logs.filter(status=NotificationLog.SUCCESS).count()
        failed_count = recent_logs.filter(status=NotificationLog.FAILED).count()
        pending_count = recent_logs.filter(status=NotificationLog.PENDING).count()
        
        # Calculate success rate
        success_rate = (successful_count / total_count * 100) if total_count > 0 else 0
        failure_rate = (failed_count / total_count * 100) if total_count > 0 else 0
        
        # Get rules statistics
        total_rules_count = NotificationRule.objects.filter(
            organization=self.request.user.organization
        ).count()
        
        active_rules_count = NotificationRule.objects.filter(
            organization=self.request.user.organization,
            is_active=True
        ).count()
        
        # Get status distribution
        status_distribution = recent_logs.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        # Get destination type distribution
        destination_types = recent_logs.values('destination__type').annotate(
            count=Count('id')
        ).order_by('destination__type')
        
        # Get top rules
        top_rules = recent_logs.values(
            'rule__name', 'rule_id'
        ).annotate(
            count=Count('id'),
            success_count=Sum(Case(
                When(status=NotificationLog.SUCCESS, then=1),
                default=0,
                output_field=IntegerField()
            ))
        ).order_by('-count')[:10]
        
        # Calculate success rate for each rule
        for rule in top_rules:
            if rule['count'] > 0:
                rule['success_rate'] = (rule['success_count'] / rule['count']) * 100
            else:
                rule['success_rate'] = 0
        
        # Build stats dictionary
        stats = {
            'total_notifications': total_count,
            'status_distribution': list(status_distribution),
            'destination_types': list(destination_types),
            'top_rules': list(top_rules),
        }
        
        # Prepare JSON data for charts
        status_labels = []
        status_data = []
        status_colors = []

        for status in status_distribution:
            status_name = NotificationLog.STATUS_CHOICES_DICT.get(status['status'], 'Unknown')
            status_labels.append(status_name)
            status_data.append(status['count'])
            
            if status['status'] == NotificationLog.SUCCESS:
                status_colors.append('#28a745')  # Green for success
            elif status['status'] == NotificationLog.FAILED:
                status_colors.append('#dc3545')  # Red for failed
            else:
                status_colors.append('#17a2b8')  # Blue for pending
        
        # Destination types data
        dest_labels = []
        dest_data = []
        
        for dest in destination_types:
            dest_type = dest['destination__type'] or 'Unknown'
            dest_type_name = NotificationDestination.TYPE_CHOICES_DICT.get(dest_type, dest_type)
            dest_labels.append(dest_type_name)
            dest_data.append(dest['count'])
        
        context.update({
            'stats': stats,
            'last_updated': now,
            'successful_count': successful_count,
            'failed_count': failed_count,
            'pending_count': pending_count,
            'success_rate': success_rate,
            'failure_rate': failure_rate,
            'total_rules_count': total_rules_count,
            'active_rules_count': active_rules_count,
            
            # JSON data for charts
            'status_labels_json': json.dumps(status_labels),
            'status_data_json': json.dumps(status_data),
            'status_colors_json': json.dumps(status_colors),
            'dest_labels_json': json.dumps(dest_labels),
            'dest_data_json': json.dumps(dest_data),
        })
        
        return context
