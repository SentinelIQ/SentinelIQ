from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.utils.translation import gettext_lazy as _
from django.db.models import Q

from accounts.views import OrgAdminRequiredMixin
from .models import Alert, AlertEvent
from .forms import AlertForm, AlertFilterForm
from cases.models import Case, CaseEvent


class AlertListView(LoginRequiredMixin, ListView):
    """List view for alerts"""
    model = Alert
    template_name = 'alerts/alert_list.html'
    context_object_name = 'alerts'
    paginate_by = 10
    
    def get_queryset(self):
        """Filter alerts by organization and parameters"""
        user = self.request.user
        
        # Base queryset - filter by organization
        if user.is_superadmin():
            queryset = Alert.objects.all()
        else:
            queryset = Alert.objects.filter(organization=user.organization)
        
        # Apply filters from form
        form = AlertFilterForm(self.request.GET)
        if form.is_valid():
            # Filter by status
            status = form.cleaned_data.get('status')
            if status:
                queryset = queryset.filter(status=status)
            
            # Filter by severity
            severity = form.cleaned_data.get('severity')
            if severity:
                queryset = queryset.filter(severity=severity)
            
            # Filter by TLP
            tlp = form.cleaned_data.get('tlp')
            if tlp:
                queryset = queryset.filter(tlp=tlp)
            
            # Filter by PAP
            pap = form.cleaned_data.get('pap')
            if pap:
                queryset = queryset.filter(pap=pap)
            
            # Filter by tag
            tag = form.cleaned_data.get('tag')
            if tag:
                queryset = queryset.filter(tags=tag)
            
            # Search in title and description
            search = form.cleaned_data.get('search')
            if search:
                queryset = queryset.filter(
                    Q(title__icontains=search) | Q(description__icontains=search)
                )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = AlertFilterForm(self.request.GET)
        return context


class AlertDetailView(LoginRequiredMixin, DetailView):
    """Detail view for alerts"""
    model = Alert
    template_name = 'alerts/alert_detail.html'
    context_object_name = 'alert'
    
    def get_queryset(self):
        """Ensure users can only see alerts from their organization"""
        user = self.request.user
        if user.is_superadmin():
            return Alert.objects.all()
        else:
            return Alert.objects.filter(organization=user.organization)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Obter eventos da timeline, ordenados do mais recente para o mais antigo
        context['timeline_events'] = self.object.timeline_events.all().order_by('-created_at')
        return context


class AlertCreateView(LoginRequiredMixin, OrgAdminRequiredMixin, CreateView):
    """Create view for alerts"""
    model = Alert
    form_class = AlertForm
    template_name = 'alerts/alert_form.html'
    success_url = reverse_lazy('alert_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization'] = self.request.user.organization
        return kwargs
    
    def form_valid(self, form):
        form.instance.organization = self.request.user.organization
        response = super().form_valid(form)
        
        # Registrar evento de criação
        self.object.add_timeline_event(
            event_type=AlertEvent.CREATED,
            title=_('Alert created'),
            user=self.request.user
        )
        
        messages.success(self.request, _('Alert created successfully.'))
        return response


class AlertUpdateView(LoginRequiredMixin, UpdateView):
    """Update view for alerts"""
    model = Alert
    form_class = AlertForm
    template_name = 'alerts/alert_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization'] = self.request.user.organization
        return kwargs
    
    def form_valid(self, form):
        old_alert = Alert.objects.get(pk=self.object.pk)
        
        # Check for status change
        if old_alert.status != self.object.status:
            self.object.log_status_change(
                user=self.request.user,
                old_status=old_alert.status,
                new_status=self.object.status
            )
        
        # Check for severity change
        if old_alert.severity != self.object.severity:
            self.object.log_severity_change(
                user=self.request.user,
                old_severity=old_alert.severity,
                new_severity=self.object.severity
            )
        
        # Check for assignee change
        if old_alert.assigned_to != self.object.assigned_to:
            self.object.log_assignee_change(
                user=self.request.user,
                old_assignee=old_alert.assigned_to,
                new_assignee=self.object.assigned_to
            )
        
        # Check for TLP change
        if old_alert.tlp != self.object.tlp:
            self.object.log_tlp_change(
                user=self.request.user,
                old_tlp=old_alert.tlp,
                new_tlp=self.object.tlp
            )
        
        # Check for PAP change
        if old_alert.pap != self.object.pap:
            self.object.log_pap_change(
                user=self.request.user,
                old_pap=old_alert.pap,
                new_pap=self.object.pap
            )
        
        # Save the form to get M2M fields updated
        response = super().form_valid(form)
        
        # Check for tags change
        old_tags = set(old_alert.tags.all())
        new_tags = set(self.object.tags.all())
        
        if old_tags != new_tags:
            self.object.log_tags_change(
                user=self.request.user,
                old_tags=old_tags,
                new_tags=new_tags
            )
        
        messages.success(self.request, _('Alert updated successfully.'))
        return response
    
    def get_success_url(self):
        return reverse('alert_detail', kwargs={'pk': self.object.pk})


class AlertDeleteView(LoginRequiredMixin, OrgAdminRequiredMixin, DeleteView):
    """Delete view for alerts"""
    model = Alert
    template_name = 'alerts/alert_confirm_delete.html'
    success_url = reverse_lazy('alert_list')
    
    def get_queryset(self):
        """Ensure users can only delete alerts from their organization"""
        user = self.request.user
        if user.is_superadmin():
            return Alert.objects.all()
        else:
            return Alert.objects.filter(organization=user.organization)
    
    def delete(self, request, *args, **kwargs):
        alert = self.get_object()
        messages.success(request, _(f'Alert "{alert.title}" was deleted successfully.'))
        return super().delete(request, *args, **kwargs)


@login_required
def escalate_to_case(request, pk):
    """Escalate an alert to a case"""
    alert = get_object_or_404(Alert, pk=pk)
    
    # Verificar se o usuário tem acesso ao alerta
    if not request.user.is_superadmin() and alert.organization != request.user.organization:
        messages.error(request, _("You don't have permission to access this alert."))
        return redirect('alert_list')
    
    # Criar um novo caso a partir do alerta
    if request.method == 'POST':
        # Mapear severidade do alerta para prioridade do caso
        severity_to_priority = {
            Alert.LOW: Case.LOW,
            Alert.MEDIUM: Case.MEDIUM,
            Alert.HIGH: Case.HIGH,
            Alert.CRITICAL: Case.CRITICAL,
        }
        
        # Criar o caso
        case = Case.objects.create(
            title=f'Case from alert: {alert.title}',
            description=f'Case escalated from alert #{alert.id}:\n\n{alert.description}',
            priority=severity_to_priority.get(alert.severity, Case.MEDIUM),
            status=Case.OPEN,
            organization=alert.organization,
            assigned_to=alert.assigned_to,  # Manter o mesmo responsável, se existir
            tlp=alert.tlp,  # Manter o mesmo TLP
            pap=alert.pap,  # Manter o mesmo PAP
        )
        
        # Adicionar o alerta aos alertas relacionados do caso
        case.related_alerts.add(alert)
        
        # Atualizar o status do alerta para "in_progress"
        if alert.status == Alert.NEW or alert.status == Alert.ACKNOWLEDGED:
            alert.status = Alert.IN_PROGRESS
            alert.save()
        
        # Registrar evento na timeline do caso
        case.add_timeline_event(
            event_type=CaseEvent.CREATED,
            title=_('Case created from alert'),
            description=_('This case was automatically created from an alert.'),
            user=request.user
        )
        
        # Adicionar evento de link de alerta
        case.log_alert_linked(request.user, alert)
        
        # Registrar evento de escalação no alerta
        alert.log_escalated_to_case(request.user, case)
        
        messages.success(request, _('Alert successfully escalated to case.'))
        return redirect('case_detail', pk=case.id)
    
    # Renderizar confirmação para escalação
    return render(request, 'alerts/alert_escalate.html', {'alert': alert})
