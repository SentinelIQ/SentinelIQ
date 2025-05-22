from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.utils import timezone
from datetime import date

from accounts.views import OrgAdminRequiredMixin
from .models import Case, CaseComment, CaseAttachment, CaseEvent, Task, ThreatCategory, TaskTemplate
from .forms import CaseForm, CaseCommentForm, CaseAttachmentForm, CaseFilterForm, CaseEventForm, TaskForm, ThreatCategoryForm, TaskTemplateFilterForm, TaskTemplateForm
from core.models import Observable


class CaseListView(LoginRequiredMixin, ListView):
    """List view for cases"""
    model = Case
    template_name = 'cases/case_list.html'
    context_object_name = 'cases'
    paginate_by = 10
    
    def get_queryset(self):
        """Filter cases by organization and parameters"""
        user = self.request.user
        
        # Base queryset - filter by organization
        if user.is_superadmin():
            queryset = Case.objects.all()
        else:
            queryset = Case.objects.filter(organization=user.organization)
        
        # Apply filters from form
        form = CaseFilterForm(self.request.GET, organization=user.organization)
        if form.is_valid():
            # Filter by status
            status = form.cleaned_data.get('status')
            if status:
                queryset = queryset.filter(status=status)
            
            # Filter by priority
            priority = form.cleaned_data.get('priority')
            if priority:
                queryset = queryset.filter(priority=priority)
            
            # Filter by assignee
            assignee = form.cleaned_data.get('assigned_to')
            if assignee:
                queryset = queryset.filter(assigned_to=assignee)
            
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
        context['filter_form'] = CaseFilterForm(
            self.request.GET, 
            organization=self.request.user.organization
        )
        context['today'] = timezone.now().date()
        return context


class CaseDetailView(LoginRequiredMixin, DetailView):
    """Detail view for cases"""
    model = Case
    template_name = 'cases/case_detail.html'
    context_object_name = 'case'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comment_form'] = CaseCommentForm()
        context['attachment_form'] = CaseAttachmentForm()
        context['event_form'] = CaseEventForm()
        context['timeline_events'] = self.object.timeline_events.all().select_related('user')
        context['today'] = date.today()
        context['current_date'] = date.today()
        
        # Contagem de tarefas para usar no template
        context['completed_tasks_count'] = self.object.tasks.filter(is_completed=True).count()
        context['pending_tasks_count'] = self.object.tasks.filter(is_completed=False).count()
        context['overdue_tasks_count'] = self.object.tasks.filter(
            is_completed=False, 
            due_date__lt=date.today()
        ).count()
        
        return context
    
    def get_queryset(self):
        """Filter cases by organization if not superadmin"""
        if self.request.user.is_superadmin:
            return Case.objects.all()
        return Case.objects.filter(organization=self.request.user.organization)


class CaseCreateView(LoginRequiredMixin, OrgAdminRequiredMixin, CreateView):
    """Create view for cases"""
    model = Case
    form_class = CaseForm
    template_name = 'cases/case_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization'] = self.request.user.organization
        return kwargs
    
    def form_valid(self, form):
        form.instance.organization = self.request.user.organization
        response = super().form_valid(form)
        
        # Log the case creation event
        self.object.add_timeline_event(
            event_type=CaseEvent.CREATED,
            title=_('Case created'),
            user=self.request.user
        )
        
        messages.success(self.request, _('Case created successfully.'))
        return response
    
    def get_success_url(self):
        return reverse('cases:case_detail', kwargs={'pk': self.object.pk})


class CaseUpdateView(LoginRequiredMixin, UpdateView):
    """Update view for cases"""
    model = Case
    form_class = CaseForm
    template_name = 'cases/case_form.html'
    
    def get_queryset(self):
        """Ensure users can only update cases from their organization"""
        user = self.request.user
        if user.is_superadmin():
            return Case.objects.all()
        else:
            return Case.objects.filter(organization=user.organization)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization'] = self.request.user.organization
        return kwargs
    
    def form_valid(self, form):
        old_case = Case.objects.get(pk=self.object.pk)
        
        # Check for status change
        if old_case.status != self.object.status:
            self.object.log_status_change(
                user=self.request.user,
                old_status=old_case.status,
                new_status=self.object.status
            )
        
        # Check for priority change
        if old_case.priority != self.object.priority:
            self.object.log_priority_change(
                user=self.request.user,
                old_priority=old_case.priority,
                new_priority=self.object.priority
            )
        
        # Check for assignee change
        if old_case.assigned_to != self.object.assigned_to:
            self.object.log_assignee_change(
                user=self.request.user,
                old_assignee=old_case.assigned_to,
                new_assignee=self.object.assigned_to
            )
        
        # Check for due date change
        if old_case.due_date != self.object.due_date:
            self.object.log_due_date_change(
                user=self.request.user,
                old_date=old_case.due_date,
                new_date=self.object.due_date
            )
        
        # Check for TLP change
        if old_case.tlp != self.object.tlp:
            self.object.log_tlp_change(
                user=self.request.user,
                old_tlp=old_case.tlp,
                new_tlp=self.object.tlp
            )
        
        # Check for PAP change
        if old_case.pap != self.object.pap:
            self.object.log_pap_change(
                user=self.request.user,
                old_pap=old_case.pap,
                new_pap=self.object.pap
            )
        
        # Save the form to get M2M fields updated
        response = super().form_valid(form)
        
        # Check for tags change
        old_tags = set(old_case.tags.all())
        new_tags = set(self.object.tags.all())
        
        if old_tags != new_tags:
            self.object.log_tags_change(
                user=self.request.user,
                old_tags=old_tags,
                new_tags=new_tags
            )
        
        # Check for related alerts change
        old_alerts = set(old_case.related_alerts.all().values_list('id', flat=True))
        new_alerts = set(self.object.related_alerts.all().values_list('id', flat=True))
        
        # Log linked alerts
        for alert_id in new_alerts - old_alerts:
            alert = self.object.related_alerts.get(id=alert_id)
            self.object.log_alert_linked(self.request.user, alert)
        
        # Log unlinked alerts
        for alert_id in old_alerts - new_alerts:
            from alerts.models import Alert
            alert = Alert.objects.get(id=alert_id)
            self.object.log_alert_unlinked(self.request.user, alert)
        
        messages.success(self.request, _('Case updated successfully.'))
        return response
    
    def get_success_url(self):
        return reverse('cases:case_detail', kwargs={'pk': self.object.pk})


class CaseDeleteView(LoginRequiredMixin, OrgAdminRequiredMixin, DeleteView):
    """Delete view for cases"""
    model = Case
    template_name = 'cases/case_confirm_delete.html'
    success_url = reverse_lazy('cases:case_list')
    
    def get_queryset(self):
        """Ensure users can only delete cases from their organization"""
        user = self.request.user
        if user.is_superadmin():
            return Case.objects.all()
        else:
            return Case.objects.filter(organization=user.organization)
    
    def delete(self, request, *args, **kwargs):
        case = self.get_object()
        messages.success(request, _(f'Case "{case.title}" was deleted successfully.'))
        return super().delete(request, *args, **kwargs)


@login_required
def add_case_comment(request, pk):
    """Add a comment to a case"""
    case = get_object_or_404(Case, pk=pk)
    
    # Check if user has access to the case
    if not request.user.is_superadmin() and case.organization != request.user.organization:
        messages.error(request, _("You don't have permission to access this case."))
        return redirect('case_list')
    
    if request.method == 'POST':
        form = CaseCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.case = case
            comment.user = request.user
            comment.save()
            # Timeline event is added in the CaseComment.save() method
            messages.success(request, _('Comment added successfully.'))
    
    return redirect('cases:case_detail', pk=pk)


@login_required
def add_case_attachment(request, pk):
    """Add an attachment to a case"""
    case = get_object_or_404(Case, pk=pk)
    
    # Check if user has access to the case
    if not request.user.is_superadmin() and case.organization != request.user.organization:
        messages.error(request, _("You don't have permission to access this case."))
        return redirect('case_list')
    
    if request.method == 'POST':
        form = CaseAttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.case = case
            attachment.uploaded_by = request.user
            attachment.save()
            # Timeline event is added in the CaseAttachment.save() method
            messages.success(request, _('Attachment added successfully.'))
    
    return redirect('cases:case_detail', pk=pk)


@login_required
def delete_case_attachment(request, pk, attachment_pk):
    """Delete an attachment from a case"""
    attachment = get_object_or_404(CaseAttachment, pk=attachment_pk, case_id=pk)
    case = attachment.case
    
    # Check if user has access to the case
    if not request.user.is_superadmin() and case.organization != request.user.organization:
        messages.error(request, _("You don't have permission to access this case."))
        return redirect('case_list')
    
    # Check if user is the uploader or has admin rights
    if request.user == attachment.uploaded_by or request.user.is_superadmin() or request.user.is_org_admin:
        # Log timeline event before deletion
        case.add_timeline_event(
            event_type=CaseEvent.CUSTOM,
            title=_('Attachment deleted'),
            description=attachment.filename,
            user=request.user
        )
        
        attachment.file.delete(save=False)
        attachment.delete()
        messages.success(request, _('Attachment deleted successfully.'))
    else:
        messages.error(request, _("You don't have permission to delete this attachment."))
    
    return redirect('cases:case_detail', pk=pk)


@login_required
def add_case_event(request, pk):
    """Add a custom event to a case's timeline"""
    case = get_object_or_404(Case, pk=pk)
    
    # Check if user has access to the case
    if not request.user.is_superadmin() and case.organization != request.user.organization:
        messages.error(request, _("You don't have permission to access this case."))
        return redirect('case_list')
    
    if request.method == 'POST':
        form = CaseEventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.case = case
            event.user = request.user
            event.save()
            messages.success(request, _('Event added to timeline successfully.'))
    
    return redirect('cases:case_detail', pk=pk)


@login_required
def add_case_task(request, case_id):
    """Add a new task to a case"""
    case = get_object_or_404(Case, pk=case_id)
    
    # Verificar acesso
    if not request.user.is_superadmin and case.organization != request.user.organization:
        messages.error(request, _("You don't have permission to add tasks to this case."))
        return redirect('case_list')
    
    if request.method == 'POST':
        form = TaskForm(request.POST, organization=request.user.organization)
        if form.is_valid():
            task = form.save(commit=False)
            task.case = case
            # Set current user for timeline events
            task.set_current_user(request.user)
            task.save()
            
            messages.success(request, _('Task added successfully.'))
            return redirect('cases:case_detail', pk=case.id)
    else:
        form = TaskForm(organization=request.user.organization)
    
    context = {
        'form': form,
        'case': case,
    }
    
    return render(request, 'cases/task_form.html', context)


@login_required
def update_case_task(request, case_id, task_id):
    """Update a task in a case"""
    case = get_object_or_404(Case, pk=case_id)
    task = get_object_or_404(Task, pk=task_id, case=case)
    
    # Verificar acesso
    if not request.user.is_superadmin and case.organization != request.user.organization:
        messages.error(request, _("You don't have permission to update tasks in this case."))
        return redirect('case_list')
    
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task, organization=request.user.organization)
        if form.is_valid():
            # Set current user for timeline events
            task = form.save(commit=False)
            task.set_current_user(request.user)
            
            # If task is marked as completed, set completed_by
            if task.is_completed and not Task.objects.get(pk=task.pk).is_completed:
                task.completed_by = request.user
            
            task.save()
            
            messages.success(request, _('Task updated successfully.'))
            return redirect('cases:case_detail', pk=case.id)
    else:
        form = TaskForm(instance=task, organization=request.user.organization)
    
    context = {
        'form': form,
        'case': case,
        'task': task,
    }
    
    return render(request, 'cases/task_form.html', context)


@login_required
def delete_case_task(request, case_id, task_id):
    """Delete a task from a case"""
    case = get_object_or_404(Case, pk=case_id)
    task = get_object_or_404(Task, pk=task_id, case=case)
    
    # Verificar acesso
    if not request.user.is_superadmin and case.organization != request.user.organization:
        messages.error(request, _("You don't have permission to delete tasks from this case."))
        return redirect('case_list')
    
    if request.method == 'POST':
        task.delete()
        messages.success(request, _('Task deleted successfully.'))
        return redirect('cases:case_detail', pk=case.id)
    
    context = {
        'case': case,
        'task': task,
    }
    
    return render(request, 'cases/task_confirm_delete.html', context)


@login_required
def toggle_task_status(request, case_id, task_id):
    """Toggle a task's completion status via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    case = get_object_or_404(Case, pk=case_id)
    task = get_object_or_404(Task, pk=task_id, case=case)
    
    # Verificar acesso
    if not request.user.is_superadmin and case.organization != request.user.organization:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    # Toggle completion status
    task.is_completed = not task.is_completed
    
    # If task is now completed, set completed info
    if task.is_completed:
        task.completed_at = timezone.now()
        task.completed_by = request.user
    else:
        task.completed_at = None
        task.completed_by = None
    
    # Set current user for timeline events
    task.set_current_user(request.user)
    task.save()
    
    return JsonResponse({
        'success': True,
        'is_completed': task.is_completed,
        'completed_at': task.completed_at.strftime('%Y-%m-%d %H:%M') if task.completed_at else None,
        'completed_by': task.completed_by.get_full_name() if task.completed_by else None
    })


# Views para gerenciar categorias de ameaças e templates de tarefas
class ThreatCategoryListView(LoginRequiredMixin, OrgAdminRequiredMixin, ListView):
    """List view for threat categories"""
    model = ThreatCategory
    template_name = 'cases/threat_category_list.html'
    context_object_name = 'categories'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Adicionar contagem de templates para cada categoria
        for category in context['categories']:
            category.template_count = TaskTemplate.objects.filter(
                threat_category=category,
                organization=self.request.user.organization
            ).count()
        return context


class ThreatCategoryDetailView(LoginRequiredMixin, DetailView):
    """Detail view for threat categories"""
    model = ThreatCategory
    template_name = 'cases/threat_category_detail.html'
    context_object_name = 'category'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Obter templates desta categoria para a organização do usuário
        context['templates'] = TaskTemplate.objects.filter(
            threat_category=self.object,
            organization=self.request.user.organization
        ).order_by('order')
        return context


class ThreatCategoryCreateView(LoginRequiredMixin, OrgAdminRequiredMixin, CreateView):
    """Create view for threat categories"""
    model = ThreatCategory
    form_class = ThreatCategoryForm
    template_name = 'cases/threat_category_form.html'
    success_url = reverse_lazy('cases:threat_category_list')
    
    def form_valid(self, form):
        messages.success(self.request, _('Threat category created successfully.'))
        return super().form_valid(form)


class ThreatCategoryUpdateView(LoginRequiredMixin, OrgAdminRequiredMixin, UpdateView):
    """Update view for threat categories"""
    model = ThreatCategory
    form_class = ThreatCategoryForm
    template_name = 'cases/threat_category_form.html'
    success_url = reverse_lazy('cases:threat_category_list')
    
    def get_success_url(self):
        return reverse('cases:threat_category_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, _('Threat category updated successfully.'))
        return super().form_valid(form)


class TaskTemplateListView(LoginRequiredMixin, ListView):
    """List view for task templates"""
    model = TaskTemplate
    template_name = 'cases/task_template_list.html'
    context_object_name = 'templates'
    paginate_by = 15
    
    def get_queryset(self):
        """Filter templates by organization and filter form params"""
        queryset = TaskTemplate.objects.filter(
            organization=self.request.user.organization
        )
        
        # Apply filters from form
        form = TaskTemplateFilterForm(self.request.GET)
        if form.is_valid():
            # Filter by threat category
            threat_category = form.cleaned_data.get('threat_category')
            if threat_category:
                queryset = queryset.filter(threat_category=threat_category)
            
            # Filter by active status
            is_active = form.cleaned_data.get('is_active')
            if is_active == '1':
                queryset = queryset.filter(is_active=True)
            elif is_active == '0':
                queryset = queryset.filter(is_active=False)
            
            # Search in title and description
            search = form.cleaned_data.get('search')
            if search:
                queryset = queryset.filter(
                    Q(title__icontains=search) | Q(description__icontains=search)
                )
        
        return queryset.order_by('threat_category', 'order', 'title')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = TaskTemplateFilterForm(self.request.GET)
        return context


class TaskTemplateCreateView(LoginRequiredMixin, OrgAdminRequiredMixin, CreateView):
    """Create view for task templates"""
    model = TaskTemplate
    form_class = TaskTemplateForm
    template_name = 'cases/task_template_form.html'
    success_url = reverse_lazy('cases:task_template_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization'] = self.request.user.organization
        return kwargs
    
    def form_valid(self, form):
        form.instance.organization = self.request.user.organization
        messages.success(self.request, _('Task template created successfully.'))
        return super().form_valid(form)
    
    def get_initial(self):
        initial = super().get_initial()
        # Pré-selecionar categoria de ameaça se fornecida na URL
        category_id = self.request.GET.get('category')
        if category_id:
            try:
                initial['threat_category'] = ThreatCategory.objects.get(pk=category_id)
            except ThreatCategory.DoesNotExist:
                pass
        return initial


class TaskTemplateUpdateView(LoginRequiredMixin, OrgAdminRequiredMixin, UpdateView):
    """Update view for task templates"""
    model = TaskTemplate
    form_class = TaskTemplateForm
    template_name = 'cases/task_template_form.html'
    
    def get_queryset(self):
        """Ensure users can only update templates from their organization"""
        return TaskTemplate.objects.filter(organization=self.request.user.organization)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization'] = self.request.user.organization
        return kwargs
    
    def get_success_url(self):
        if 'category' in self.request.GET:
            # Voltar para a página de detalhes da categoria
            return reverse('cases:threat_category_detail', kwargs={'pk': self.request.GET.get('category')})
        return reverse('cases:task_template_list')
    
    def form_valid(self, form):
        messages.success(self.request, _('Task template updated successfully.'))
        return super().form_valid(form)


class TaskTemplateDeleteView(LoginRequiredMixin, OrgAdminRequiredMixin, DeleteView):
    """Delete view for task templates"""
    model = TaskTemplate
    template_name = 'cases/task_template_confirm_delete.html'
    success_url = reverse_lazy('cases:task_template_list')
    
    def get_queryset(self):
        """Ensure users can only delete templates from their organization"""
        return TaskTemplate.objects.filter(organization=self.request.user.organization)
    
    def delete(self, request, *args, **kwargs):
        template = self.get_object()
        messages.success(request, _(f'Task template "{template.title}" was deleted successfully.'))
        return super().delete(request, *args, **kwargs)
    
    def get_success_url(self):
        if 'category' in self.request.GET:
            # Voltar para a página de detalhes da categoria
            return reverse('cases:threat_category_detail', kwargs={'pk': self.request.GET.get('category')})
        return reverse('cases:task_template_list')


@login_required
def clone_task_template(request, pk):
    """Clone a task template"""
    template = get_object_or_404(TaskTemplate, pk=pk, organization=request.user.organization)
    
    if request.method == 'POST':
        # Criar uma cópia do template
        new_template = TaskTemplate.objects.create(
            title=f"{template.title} (Clone)",
            description=template.description,
            priority=template.priority,
            threat_category=template.threat_category,
            organization=request.user.organization,
            is_active=template.is_active,
            order=template.order,
            due_days=template.due_days
        )
        
        messages.success(request, _('Task template cloned successfully.'))
        return redirect('cases:task_template_update', pk=new_template.pk)
    
    return render(request, 'cases/task_template_clone.html', {'template': template})


@login_required
def bulk_create_templates(request):
    """Bulk create task templates from predefined options"""
    if request.method == 'POST':
        # Obter a categoria selecionada
        category_id = request.POST.get('category')
        template_type = request.POST.get('template_type')
        
        try:
            category = ThreatCategory.objects.get(pk=category_id)
            
            templates_created = 0
            
            # Criar templates baseados no tipo selecionado
            if template_type == 'phishing':
                templates = [
                    {
                        'title': 'Verificar domínio de origem',
                        'description': 'Verificar se o domínio do e-mail de phishing é legítimo ou se trata-se de um domínio malicioso/falsificado.',
                        'priority': TaskTemplate.HIGH,
                        'order': 1,
                        'due_days': 1
                    },
                    {
                        'title': 'Verificar anexos/URLs',
                        'description': 'Analisar anexos ou URLs contidos no e-mail de phishing para identificação de malware ou páginas fraudulentas.',
                        'priority': TaskTemplate.HIGH,
                        'order': 2,
                        'due_days': 1
                    },
                    {
                        'title': 'Identificar usuários impactados',
                        'description': 'Levantar lista de usuários que receberam o e-mail e verificar se algum interagiu com o conteúdo malicioso.',
                        'priority': TaskTemplate.MEDIUM,
                        'order': 3,
                        'due_days': 2
                    }
                ]
            elif template_type == 'malware':
                templates = [
                    {
                        'title': 'Identificar malware',
                        'description': 'Identificar o tipo e família do malware através de análise de assinaturas e comportamentos.',
                        'priority': TaskTemplate.HIGH,
                        'order': 1,
                        'due_days': 1
                    },
                    {
                        'title': 'Isolar sistemas afetados',
                        'description': 'Isolar os sistemas afetados da rede para evitar propagação do malware.',
                        'priority': TaskTemplate.HIGH,
                        'order': 2,
                        'due_days': 1
                    },
                    {
                        'title': 'Investigar vetor de infecção',
                        'description': 'Determinar como o malware entrou no ambiente (e-mail, download, mídia removível, exploração de vulnerabilidade, etc.).',
                        'priority': TaskTemplate.MEDIUM,
                        'order': 3,
                        'due_days': 2
                    }
                ]
            else:
                templates = []
            
            # Criar os templates
            for template_data in templates:
                template = TaskTemplate.objects.create(
                    title=template_data['title'],
                    description=template_data['description'],
                    priority=template_data['priority'],
                    threat_category=category,
                    organization=request.user.organization,
                    order=template_data['order'],
                    due_days=template_data['due_days'],
                    is_active=True
                )
                templates_created += 1
            
            if templates_created > 0:
                messages.success(request, _(f'Created {templates_created} task templates for {category}.'))
            else:
                messages.warning(request, _('No templates were created. Template type not supported.'))
            
            return redirect('cases:threat_category_detail', pk=category.pk)
        
        except ThreatCategory.DoesNotExist:
            messages.error(request, _('The selected threat category does not exist.'))
    
    # Obter todas as categorias de ameaça
    categories = ThreatCategory.objects.all()
    
    return render(request, 'cases/task_template_bulk_create.html', {
        'categories': categories
    })


@login_required
def toggle_template_status(request, pk):
    """Toggle active status of a task template"""
    template = get_object_or_404(TaskTemplate, pk=pk, organization=request.user.organization)
    
    if request.method == 'POST':
        template.is_active = not template.is_active
        template.save()
        
        status_text = _('activated') if template.is_active else _('deactivated')
        messages.success(request, _(f'Task template "{template.title}" {status_text} successfully.'))
        
        # Redirect to the previous page
        next_url = request.POST.get('next', reverse('cases:task_template_list'))
        return redirect(next_url)
    
    return render(request, 'cases/task_template_toggle_status.html', {'template': template})
