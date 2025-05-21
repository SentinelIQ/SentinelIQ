from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, Count
from django.http import JsonResponse
from django.db import IntegrityError
from django.utils import timezone

from accounts.views import OrgAdminRequiredMixin
from .models import Tag, Observable, MitreTactic, MitreTechnique, MitreSubTechnique, MitreAttackGroup
from .forms import TagForm, ObservableForm, ObservableFilterForm, MitreAttackSelectionForm, MitreAttackGroupForm
from alerts.models import Alert
from cases.models import Case


def home(request):
    """Home page view"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/home.html')


def handler404(request, exception):
    """404 error handler"""
    return render(request, 'core/404.html', status=404)


def handler500(request):
    """500 error handler"""
    return render(request, 'core/500.html', status=500)


class TagListView(LoginRequiredMixin, ListView):
    """List view for tags"""
    model = Tag
    template_name = 'core/tag_list.html'
    context_object_name = 'tags'
    paginate_by = 20
    
    def get_queryset(self):
        """Filter tags by search terms"""
        queryset = Tag.objects.all()
        
        # Apply search filter
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        return context


class TagCreateView(LoginRequiredMixin, OrgAdminRequiredMixin, CreateView):
    """Create view for tags"""
    model = Tag
    form_class = TagForm
    template_name = 'core/tag_form.html'
    success_url = reverse_lazy('tag_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_initial(self):
        initial = super().get_initial()
        alert_id = self.request.GET.get('alert_id')
        case_id = self.request.GET.get('case_id')
        
        if alert_id:
            try:
                alert = Alert.objects.get(id=alert_id, organization=self.request.user.organization)
                initial['alert'] = alert.id
            except Alert.DoesNotExist:
                pass
        
        if case_id:
            try:
                case = Case.objects.get(id=case_id, organization=self.request.user.organization)
                initial['case'] = case.id
            except Case.DoesNotExist:
                pass
        
        return initial
    
    def form_valid(self, form):
        tag = form.save()
        
        # Associar a tag ao alerta selecionado, se houver
        if 'alert' in form.cleaned_data and form.cleaned_data['alert']:
            alert = form.cleaned_data['alert']
            alert.tags.add(tag)
            # Registrar na timeline do alerta
            alert.log_tags_change(self.request.user, [], [tag])
            messages.success(self.request, f'Tag criada e associada ao alerta {alert.title} com sucesso!')
            self.success_url = reverse_lazy('alert_detail', kwargs={'pk': alert.id})
        
        # Associar a tag ao caso selecionado, se houver
        elif 'case' in form.cleaned_data and form.cleaned_data['case']:
            case = form.cleaned_data['case']
            case.tags.add(tag)
            # Registrar na timeline do caso
            case.log_tags_change(self.request.user, [], [tag])
            messages.success(self.request, f'Tag criada e associada ao caso {case.title} com sucesso!')
            self.success_url = reverse_lazy('case_detail', kwargs={'pk': case.id})
        else:
            messages.success(self.request, 'Tag criada com sucesso!')
            
        return super(TagCreateView, self).form_valid(form)


class TagUpdateView(LoginRequiredMixin, OrgAdminRequiredMixin, UpdateView):
    """Update view for tags"""
    model = Tag
    form_class = TagForm
    template_name = 'core/tag_form.html'
    success_url = reverse_lazy('tag_list')
    
    def form_valid(self, form):
        messages.success(self.request, _('Tag updated successfully.'))
        return super().form_valid(form)


class TagDeleteView(LoginRequiredMixin, OrgAdminRequiredMixin, DeleteView):
    """Delete view for tags"""
    model = Tag
    template_name = 'core/tag_confirm_delete.html'
    success_url = reverse_lazy('tag_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('Tag deleted successfully.'))
        return super().delete(request, *args, **kwargs)


@login_required
def dashboard(request):
    """Dashboard view"""
    # Get statistics
    total_alerts = Alert.objects.filter(organization=request.user.organization).count()
    active_alerts = Alert.objects.filter(
        organization=request.user.organization,
        status__in=['new', 'acknowledged', 'in_progress']
    ).count()
    
    total_cases = Case.objects.filter(organization=request.user.organization).count()
    active_cases = Case.objects.filter(
        organization=request.user.organization,
        status__in=['open', 'in_progress', 'pending']
    ).count()
    
    # Usar a organização direta do observable em vez de relacionamentos
    total_observables = Observable.objects.filter(
        organization=request.user.organization
    ).count()
    
    malicious_observables = Observable.objects.filter(
        organization=request.user.organization,
        is_malicious=True
    ).count()
    
    # Get recent alerts
    recent_alerts = Alert.objects.filter(
        organization=request.user.organization
    ).order_by('-created_at')[:5]
    
    # Get recent cases
    recent_cases = Case.objects.filter(
        organization=request.user.organization
    ).order_by('-created_at')[:5]
    
    context = {
        'total_alerts': total_alerts,
        'active_alerts': active_alerts,
        'total_cases': total_cases,
        'active_cases': active_cases,
        'total_observables': total_observables,
        'malicious_observables': malicious_observables,
        'recent_alerts': recent_alerts,
        'recent_cases': recent_cases,
    }
    
    return render(request, 'core/dashboard.html', context)


@login_required
def tag_list(request):
    """List all tags"""
    tags = Tag.objects.all().annotate(
        alert_count=Count('alerts'), 
        case_count=Count('cases')
    )
    
    context = {
        'tags': tags
    }
    
    return render(request, 'core/tag_list.html', context)


@login_required
def tag_create(request):
    """Create a new tag"""
    # Obter parâmetros de URL para alerta ou caso pré-selecionado
    alert_id = request.GET.get('alert_id')
    case_id = request.GET.get('case_id')
    
    if request.method == 'POST':
        form = TagForm(request.POST, user=request.user)
        if form.is_valid():
            tag = form.save()
            
            # Associar a tag ao alerta selecionado, se houver
            if 'alert' in form.cleaned_data and form.cleaned_data['alert']:
                alert = form.cleaned_data['alert']
                alert.tags.add(tag)
                # Registrar na timeline do alerta
                alert.log_tags_change(request.user, [], [tag])
                messages.success(request, f'Tag criada e associada ao alerta {alert.title} com sucesso!')
                return redirect('alert_detail', pk=alert.id)
            
            # Associar a tag ao caso selecionado, se houver
            elif 'case' in form.cleaned_data and form.cleaned_data['case']:
                case = form.cleaned_data['case']
                case.tags.add(tag)
                # Registrar na timeline do caso
                case.log_tags_change(request.user, [], [tag])
                messages.success(request, f'Tag criada e associada ao caso {case.title} com sucesso!')
                return redirect('case_detail', pk=case.id)
            else:
                messages.success(request, 'Tag criada com sucesso, mas não foi associada a nenhum alerta ou caso!')
            
            return redirect('tag_list')
    else:
        initial_data = {}
        
        # Se houver um alerta_id na query string, pré-selecioná-lo no formulário
        if alert_id:
            try:
                alert = Alert.objects.get(id=alert_id, organization=request.user.organization)
                initial_data['alert'] = alert.id
            except Alert.DoesNotExist:
                pass
        
        # Se houver um case_id na query string, pré-selecioná-lo no formulário
        if case_id:
            try:
                case = Case.objects.get(id=case_id, organization=request.user.organization)
                initial_data['case'] = case.id
            except Case.DoesNotExist:
                pass
        
        form = TagForm(initial=initial_data, user=request.user)
    
    context = {
        'form': form,
        'title': 'Criar Nova Tag'
    }
    
    return render(request, 'core/tag_form.html', context)


@login_required
def tag_update(request, pk):
    """Update an existing tag"""
    tag = get_object_or_404(Tag, pk=pk)
    
    if request.method == 'POST':
        form = TagForm(request.POST, instance=tag)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tag atualizada com sucesso!')
            return redirect('tag_list')
    else:
        form = TagForm(instance=tag)
    
    context = {
        'form': form,
        'tag': tag,
        'title': 'Editar Tag'
    }
    
    return render(request, 'core/tag_form.html', context)


@login_required
def tag_delete(request, pk):
    """Delete a tag"""
    tag = get_object_or_404(Tag, pk=pk)
    
    if request.method == 'POST':
        tag.delete()
        messages.success(request, 'Tag excluída com sucesso!')
        return redirect('tag_list')
    
    context = {
        'tag': tag
    }
    
    return render(request, 'core/tag_confirm_delete.html', context)


@login_required
def observable_list(request):
    """List all observables"""
    filter_form = ObservableFilterForm(request.GET)
    
    # Usar a organização direta do observable em vez de relacionamentos
    observables = Observable.objects.filter(
        organization=request.user.organization
    )
    
    # Apply filters if provided
    if filter_form.is_valid():
        # Filter by type
        if filter_form.cleaned_data.get('type'):
            observables = observables.filter(type=filter_form.cleaned_data.get('type'))
        
        # Filter by search term (value or description)
        if filter_form.cleaned_data.get('search'):
            search_term = filter_form.cleaned_data.get('search')
            observables = observables.filter(
                Q(value__icontains=search_term) | 
                Q(description__icontains=search_term)
            )
        
        # Filter by malicious flag
        if filter_form.cleaned_data.get('is_malicious') == 'true':
            observables = observables.filter(is_malicious=True)
        elif filter_form.cleaned_data.get('is_malicious') == 'false':
            observables = observables.filter(is_malicious=False)
        
        # Filter by confidence level
        if filter_form.cleaned_data.get('confidence'):
            observables = observables.filter(confidence=filter_form.cleaned_data.get('confidence'))
    
    # Annotate with counts for related alerts and cases
    observables = observables.annotate(
        alert_count=Count('alerts', distinct=True),
        case_count=Count('cases', distinct=True)
    )
    
    context = {
        'observables': observables,
        'filter_form': filter_form
    }
    
    return render(request, 'core/observable_list.html', context)


@login_required
def observable_detail(request, pk):
    """View observable details"""
    observable = get_object_or_404(Observable, pk=pk)
    
    # Update the last_seen time
    observable.last_seen = timezone.now()
    observable.save(update_fields=['last_seen'])
    
    # Get related alerts and cases from the user's organization
    related_alerts = observable.alerts.filter(organization=request.user.organization)
    related_cases = observable.cases.filter(organization=request.user.organization)
    
    context = {
        'observable': observable,
        'related_alerts': related_alerts,
        'related_cases': related_cases
    }
    
    return render(request, 'core/observable_detail.html', context)


@login_required
def observable_create(request):
    """Create a new observable"""
    if request.method == 'POST':
        form = ObservableForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                # Salvar o observable com a organização correta
                observable = form.save(commit=False)
                observable.organization = request.user.organization
                observable.last_seen = timezone.now()  # Inicializar o campo last_seen
                observable.save()
                
                messages.success(request, 'Observable criado com sucesso!')
                
                # Verificar e associar a alertas/casos selecionados no formulário
                alert = form.cleaned_data.get('alert')
                case = form.cleaned_data.get('case')
                
                if alert:
                    alert.observables.add(observable)
                    alert.log_observable_added(request.user, observable)
                    messages.success(request, f'Observable associado ao alerta {alert.title} com sucesso!')
                    return redirect('alert_detail', pk=alert.id)
                
                elif case:
                    case.observables.add(observable)
                    case.log_observable_added(request.user, observable)
                    messages.success(request, f'Observable associado ao caso {case.title} com sucesso!')
                    return redirect('case_detail', pk=case.id)
                
                # Comportamento anterior de redirecionamento baseado em parâmetros na URL
                elif 'alert_id' in request.GET:
                    alert_id = request.GET.get('alert_id')
                    alert = get_object_or_404(Alert, pk=alert_id, organization=request.user.organization)
                    alert.observables.add(observable)
                    alert.log_observable_added(request.user, observable)
                    return redirect('alert_detail', pk=alert_id)
                
                elif 'case_id' in request.GET:
                    case_id = request.GET.get('case_id')
                    case = get_object_or_404(Case, pk=case_id, organization=request.user.organization)
                    case.observables.add(observable)
                    case.log_observable_added(request.user, observable)
                    return redirect('case_detail', pk=case_id)
                
                return redirect('observable_list')
            except IntegrityError:
                form.add_error(None, 'Este valor de observable já existe com este tipo. Os observables devem ser únicos por tipo e valor.')
    else:
        # Pré-preencher o formulário com valores de case_id ou alert_id da URL
        initial_data = {}
        
        alert_id = request.GET.get('alert_id')
        case_id = request.GET.get('case_id')
        
        if alert_id:
            try:
                alert = Alert.objects.get(id=alert_id, organization=request.user.organization)
                initial_data['alert'] = alert.id
            except Alert.DoesNotExist:
                pass
        
        if case_id:
            try:
                case = Case.objects.get(id=case_id, organization=request.user.organization)
                initial_data['case'] = case.id
            except Case.DoesNotExist:
                pass
        
        form = ObservableForm(initial=initial_data, user=request.user)
    
    context = {
        'form': form,
        'title': 'Criar Novo Observable'
    }
    
    return render(request, 'core/observable_form.html', context)


@login_required
def observable_update(request, pk):
    """Update an existing observable"""
    observable = get_object_or_404(Observable, pk=pk, organization=request.user.organization)
    
    if request.method == 'POST':
        form = ObservableForm(request.POST, instance=observable, user=request.user)
        if form.is_valid():
            observable = form.save()
            
            # Verificar e associar a alertas/casos selecionados no formulário
            alert = form.cleaned_data.get('alert')
            case = form.cleaned_data.get('case')
            
            if alert and alert not in observable.alerts.all():
                alert.observables.add(observable)
                alert.log_observable_added(request.user, observable)
                messages.success(request, f'Observable associado ao alerta {alert.title} com sucesso!')
                return redirect('alert_detail', pk=alert.id)
            
            elif case and case not in observable.cases.all():
                case.observables.add(observable)
                case.log_observable_added(request.user, observable)
                messages.success(request, f'Observable associado ao caso {case.title} com sucesso!')
                return redirect('case_detail', pk=case.id)
            else:
                messages.success(request, 'Observable atualizado com sucesso!')
                return redirect('observable_detail', pk=observable.pk)
    else:
        # Buscar alertas e casos relacionados para facilitar a seleção
        related_alerts = observable.alerts.filter(organization=request.user.organization)
        related_cases = observable.cases.filter(organization=request.user.organization)
        
        # Pré-selecionar o primeiro alerta ou caso se houver algum
        initial_data = {}
        if related_alerts.exists():
            initial_data['alert'] = related_alerts.first().id
        elif related_cases.exists():
            initial_data['case'] = related_cases.first().id
            
        form = ObservableForm(instance=observable, initial=initial_data, user=request.user)
    
    context = {
        'form': form,
        'observable': observable,
        'title': 'Editar Observable'
    }
    
    return render(request, 'core/observable_form.html', context)


@login_required
def observable_delete(request, pk):
    """Delete an observable"""
    observable = get_object_or_404(Observable, pk=pk)
    
    if request.method == 'POST':
        observable.delete()
        messages.success(request, 'Observable excluído com sucesso!')
        return redirect('observable_list')
    
    context = {
        'observable': observable
    }
    
    return render(request, 'core/observable_confirm_delete.html', context)


@login_required
def add_alert_observable(request, alert_id):
    """Add an observable to an alert"""
    alert = get_object_or_404(Alert, pk=alert_id)
    
    # Check if user has permission to modify this alert
    if alert.organization != request.user.organization:
        messages.error(request, 'Você não tem permissão para modificar este alerta.')
        return redirect('alert_list')
    
    if request.method == 'POST':
        if 'observable_id' in request.POST:
            # Add existing observable
            observable_id = request.POST.get('observable_id')
            observable = get_object_or_404(Observable, pk=observable_id)
            alert.observables.add(observable)
            alert.log_observable_added(request.user, observable)
            messages.success(request, 'Observable adicionado ao alerta com sucesso!')
        else:
            # Create new observable
            form = ObservableForm(request.POST)
            if form.is_valid():
                try:
                    observable = form.save(commit=False)
                    observable.organization = request.user.organization
                    observable.save()
                    alert.observables.add(observable)
                    alert.log_observable_added(request.user, observable)
                    messages.success(request, 'Observable criado e adicionado ao alerta com sucesso!')
                except IntegrityError:
                    messages.error(request, 'Este valor de observable já existe com este tipo.')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'Erro no campo {field}: {error}')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        return redirect('alert_detail', alert_id)
    
    # GET request: show form to add observable
    existing_observables = Observable.objects.exclude(alerts=alert).order_by('type', 'value')
    form = ObservableForm()
    
    context = {
        'alert': alert,
        'form': form,
        'existing_observables': existing_observables
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'core/partials/add_observable_form.html', context)
    return render(request, 'core/add_alert_observable.html', context)


@login_required
def remove_alert_observable(request, alert_id, observable_id):
    """Remove an observable from an alert"""
    alert = get_object_or_404(Alert, pk=alert_id)
    observable = get_object_or_404(Observable, pk=observable_id)
    
    # Check if user has permission to modify this alert
    if alert.organization != request.user.organization:
        messages.error(request, 'Você não tem permissão para modificar este alerta.')
        return redirect('alert_list')
    
    if request.method == 'POST':
        if observable in alert.observables.all():
            alert.observables.remove(observable)
            alert.log_observable_removed(request.user, observable)
            messages.success(request, 'Observable removido do alerta com sucesso!')
        else:
            messages.error(request, 'Este observable não está associado ao alerta.')
    
    return redirect('alert_detail', alert_id)


@login_required
def add_case_observable(request, case_id):
    """Add an observable to a case"""
    case = get_object_or_404(Case, pk=case_id)
    
    # Check if user has permission to modify this case
    if case.organization != request.user.organization:
        messages.error(request, 'Você não tem permissão para modificar este caso.')
        return redirect('case_list')
    
    if request.method == 'POST':
        if 'observable_id' in request.POST:
            # Add existing observable
            observable_id = request.POST.get('observable_id')
            observable = get_object_or_404(Observable, pk=observable_id)
            case.observables.add(observable)
            case.log_observable_added(request.user, observable)
            messages.success(request, 'Observable adicionado ao caso com sucesso!')
        else:
            # Create new observable
            form = ObservableForm(request.POST)
            if form.is_valid():
                try:
                    observable = form.save(commit=False)
                    observable.organization = request.user.organization
                    observable.save()
                    case.observables.add(observable)
                    case.log_observable_added(request.user, observable)
                    messages.success(request, 'Observable criado e adicionado ao caso com sucesso!')
                except IntegrityError:
                    messages.error(request, 'Este valor de observable já existe com este tipo.')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'Erro no campo {field}: {error}')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        return redirect('case_detail', case_id)
    
    # GET request: show form to add observable
    existing_observables = Observable.objects.exclude(cases=case).order_by('type', 'value')
    form = ObservableForm()
    
    context = {
        'case': case,
        'form': form,
        'existing_observables': existing_observables
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'core/partials/add_observable_form.html', context)
    return render(request, 'core/add_case_observable.html', context)


@login_required
def remove_case_observable(request, case_id, observable_id):
    """Remove an observable from a case"""
    case = get_object_or_404(Case, pk=case_id)
    observable = get_object_or_404(Observable, pk=observable_id)
    
    # Check if user has permission to modify this case
    if case.organization != request.user.organization:
        messages.error(request, 'Você não tem permissão para modificar este caso.')
        return redirect('case_list')
    
    if request.method == 'POST':
        if observable in case.observables.all():
            case.observables.remove(observable)
            case.log_observable_removed(request.user, observable)
            messages.success(request, 'Observable removido do caso com sucesso!')
        else:
            messages.error(request, 'Este observable não está associado ao caso.')
    
    return redirect('case_detail', case_id)


@login_required
def mitre_attack_list(request):
    """List all MITRE ATT&CK elements"""
    tactics = MitreTactic.objects.all().order_by('tactic_id')
    
    # Get any selected tactic for filtering
    selected_tactic_id = request.GET.get('tactic')
    selected_tactic = None
    
    if selected_tactic_id:
        try:
            selected_tactic = MitreTactic.objects.get(pk=selected_tactic_id)
            techniques = MitreTechnique.objects.filter(tactics=selected_tactic).order_by('technique_id')
        except MitreTactic.DoesNotExist:
            techniques = MitreTechnique.objects.all().order_by('technique_id')
    else:
        techniques = MitreTechnique.objects.all().order_by('technique_id')
    
    # Get any selected technique for filtering
    selected_technique_id = request.GET.get('technique')
    selected_technique = None
    
    if selected_technique_id:
        try:
            selected_technique = MitreTechnique.objects.get(pk=selected_technique_id)
            subtechniques = MitreSubTechnique.objects.filter(parent_technique=selected_technique).order_by('sub_technique_id')
        except MitreTechnique.DoesNotExist:
            subtechniques = MitreSubTechnique.objects.all().order_by('sub_technique_id')
    else:
        subtechniques = MitreSubTechnique.objects.all().order_by('sub_technique_id')
    
    context = {
        'tactics': tactics,
        'techniques': techniques,
        'subtechniques': subtechniques,
        'selected_tactic': selected_tactic,
        'selected_technique': selected_technique
    }
    
    return render(request, 'core/mitre_attack_list.html', context)


@login_required
def add_case_mitre_attack(request, case_id):
    """Add MITRE ATT&CK elements to a case"""
    case = get_object_or_404(Case, pk=case_id)
    
    # Check if user has permission to modify this case
    if case.organization != request.user.organization:
        messages.error(request, 'Você não tem permissão para modificar este caso.')
        return redirect('case_list')
    
    if request.method == 'POST':
        form = MitreAttackSelectionForm(request.POST)
        
        if form.is_valid():
            tactic = form.cleaned_data.get('tactic')
            technique = form.cleaned_data.get('technique')
            subtechnique = form.cleaned_data.get('subtechnique')
            
            if tactic:
                case.mitre_tactics.add(tactic)
                case.log_mitre_attack_added(request.user, 'tactic', tactic)
                messages.success(request, f'Tática MITRE ATT&CK adicionada ao caso: {tactic}')
            
            if technique:
                case.mitre_techniques.add(technique)
                case.log_mitre_attack_added(request.user, 'technique', technique)
                messages.success(request, f'Técnica MITRE ATT&CK adicionada ao caso: {technique}')
            
            if subtechnique:
                case.mitre_subtechniques.add(subtechnique)
                case.log_mitre_attack_added(request.user, 'subtechnique', subtechnique)
                messages.success(request, f'Sub-técnica MITRE ATT&CK adicionada ao caso: {subtechnique}')
            
            if not any([tactic, technique, subtechnique]):
                messages.warning(request, 'Nenhum elemento MITRE ATT&CK selecionado.')
            
            return redirect('case_detail', case_id)
    else:
        # GET request: show form to add MITRE ATT&CK elements
        tactic_id = request.GET.get('tactic')
        technique_id = request.GET.get('technique')
        
        initial = {}
        if tactic_id:
            try:
                initial['tactic'] = MitreTactic.objects.get(pk=tactic_id)
            except MitreTactic.DoesNotExist:
                pass
        
        if technique_id:
            try:
                initial['technique'] = MitreTechnique.objects.get(pk=technique_id)
            except MitreTechnique.DoesNotExist:
                pass
        
        form = MitreAttackSelectionForm(initial=initial)
    
    context = {
        'case': case,
        'form': form,
        'existing_tactics': case.mitre_tactics.all(),
        'existing_techniques': case.mitre_techniques.all(),
        'existing_subtechniques': case.mitre_subtechniques.all(),
    }
    
    return render(request, 'core/add_case_mitre_attack.html', context)


@login_required
def remove_case_mitre_attack(request, case_id, item_type, item_id):
    """Remove MITRE ATT&CK elements from a case"""
    case = get_object_or_404(Case, pk=case_id)
    
    # Check if user has permission to modify this case
    if case.organization != request.user.organization:
        messages.error(request, 'Você não tem permissão para modificar este caso.')
        return redirect('case_list')
    
    if request.method == 'POST':
        if item_type == 'tactic':
            try:
                item = MitreTactic.objects.get(pk=item_id)
                case.mitre_tactics.remove(item)
                case.log_mitre_attack_removed(request.user, 'tactic', item)
                messages.success(request, f'Tática MITRE ATT&CK removida do caso: {item}')
            except MitreTactic.DoesNotExist:
                messages.error(request, 'Tática MITRE ATT&CK não encontrada.')
        
        elif item_type == 'technique':
            try:
                item = MitreTechnique.objects.get(pk=item_id)
                case.mitre_techniques.remove(item)
                case.log_mitre_attack_removed(request.user, 'technique', item)
                messages.success(request, f'Técnica MITRE ATT&CK removida do caso: {item}')
            except MitreTechnique.DoesNotExist:
                messages.error(request, 'Técnica MITRE ATT&CK não encontrada.')
        
        elif item_type == 'subtechnique':
            try:
                item = MitreSubTechnique.objects.get(pk=item_id)
                case.mitre_subtechniques.remove(item)
                case.log_mitre_attack_removed(request.user, 'subtechnique', item)
                messages.success(request, f'Sub-técnica MITRE ATT&CK removida do caso: {item}')
            except MitreSubTechnique.DoesNotExist:
                messages.error(request, 'Sub-técnica MITRE ATT&CK não encontrada.')
        
        else:
            messages.error(request, 'Tipo de item MITRE ATT&CK inválido.')
    
    return redirect('case_detail', case_id)


@login_required
def add_alert_mitre_attack(request, alert_id):
    """Add MITRE ATT&CK elements to an alert"""
    alert = get_object_or_404(Alert, pk=alert_id)
    
    # Check if user has permission to modify this alert
    if alert.organization != request.user.organization:
        messages.error(request, 'Você não tem permissão para modificar este alerta.')
        return redirect('alert_list')
    
    if request.method == 'POST':
        form = MitreAttackSelectionForm(request.POST)
        
        if form.is_valid():
            tactic = form.cleaned_data.get('tactic')
            technique = form.cleaned_data.get('technique')
            subtechnique = form.cleaned_data.get('subtechnique')
            
            if tactic:
                alert.mitre_tactics.add(tactic)
                alert.log_mitre_attack_added(request.user, 'tactic', tactic)
                messages.success(request, f'Tática MITRE ATT&CK adicionada ao alerta: {tactic}')
            
            if technique:
                alert.mitre_techniques.add(technique)
                alert.log_mitre_attack_added(request.user, 'technique', technique)
                messages.success(request, f'Técnica MITRE ATT&CK adicionada ao alerta: {technique}')
            
            if subtechnique:
                alert.mitre_subtechniques.add(subtechnique)
                alert.log_mitre_attack_added(request.user, 'subtechnique', subtechnique)
                messages.success(request, f'Sub-técnica MITRE ATT&CK adicionada ao alerta: {subtechnique}')
            
            if not any([tactic, technique, subtechnique]):
                messages.warning(request, 'Nenhum elemento MITRE ATT&CK selecionado.')
            
            return redirect('alert_detail', alert_id)
    else:
        # GET request: show form to add MITRE ATT&CK elements
        tactic_id = request.GET.get('tactic')
        technique_id = request.GET.get('technique')
        
        initial = {}
        if tactic_id:
            try:
                initial['tactic'] = MitreTactic.objects.get(pk=tactic_id)
            except MitreTactic.DoesNotExist:
                pass
        
        if technique_id:
            try:
                initial['technique'] = MitreTechnique.objects.get(pk=technique_id)
            except MitreTechnique.DoesNotExist:
                pass
        
        form = MitreAttackSelectionForm(initial=initial)
    
    context = {
        'alert': alert,
        'form': form,
        'existing_tactics': alert.mitre_tactics.all(),
        'existing_techniques': alert.mitre_techniques.all(),
        'existing_subtechniques': alert.mitre_subtechniques.all(),
    }
    
    return render(request, 'core/add_alert_mitre_attack.html', context)


@login_required
def remove_alert_mitre_attack(request, alert_id, item_type, item_id):
    """Remove MITRE ATT&CK elements from an alert"""
    alert = get_object_or_404(Alert, pk=alert_id)
    
    # Check if user has permission to modify this alert
    if alert.organization != request.user.organization:
        messages.error(request, 'Você não tem permissão para modificar este alerta.')
        return redirect('alert_list')
    
    if request.method == 'POST':
        if item_type == 'tactic':
            try:
                item = MitreTactic.objects.get(pk=item_id)
                alert.mitre_tactics.remove(item)
                alert.log_mitre_attack_removed(request.user, 'tactic', item)
                messages.success(request, f'Tática MITRE ATT&CK removida do alerta: {item}')
            except MitreTactic.DoesNotExist:
                messages.error(request, 'Tática MITRE ATT&CK não encontrada.')
        
        elif item_type == 'technique':
            try:
                item = MitreTechnique.objects.get(pk=item_id)
                alert.mitre_techniques.remove(item)
                alert.log_mitre_attack_removed(request.user, 'technique', item)
                messages.success(request, f'Técnica MITRE ATT&CK removida do alerta: {item}')
            except MitreTechnique.DoesNotExist:
                messages.error(request, 'Técnica MITRE ATT&CK não encontrada.')
        
        elif item_type == 'subtechnique':
            try:
                item = MitreSubTechnique.objects.get(pk=item_id)
                alert.mitre_subtechniques.remove(item)
                alert.log_mitre_attack_removed(request.user, 'subtechnique', item)
                messages.success(request, f'Sub-técnica MITRE ATT&CK removida do alerta: {item}')
            except MitreSubTechnique.DoesNotExist:
                messages.error(request, 'Sub-técnica MITRE ATT&CK não encontrada.')
        
        else:
            messages.error(request, 'Tipo de item MITRE ATT&CK inválido.')
    
    return redirect('alert_detail', alert_id)


@login_required
def api_get_techniques_by_tactic(request, tactic_id):
    """API endpoint to get techniques for a specific tactic"""
    tactic = get_object_or_404(MitreTactic, pk=tactic_id)
    techniques = MitreTechnique.objects.filter(tactics=tactic).order_by('technique_id')
    
    data = []
    for technique in techniques:
        data.append({
            'id': technique.id,
            'technique_id': technique.technique_id,
            'name': technique.name,
        })
    
    return JsonResponse(data, safe=False)


@login_required
def api_get_subtechniques_by_technique(request, technique_id):
    """API endpoint to get sub-techniques for a specific technique"""
    technique = get_object_or_404(MitreTechnique, pk=technique_id)
    subtechniques = MitreSubTechnique.objects.filter(parent_technique=technique).order_by('sub_technique_id')
    
    data = []
    for subtechnique in subtechniques:
        data.append({
            'id': subtechnique.id,
            'sub_technique_id': subtechnique.sub_technique_id,
            'name': subtechnique.name,
        })
    
    return JsonResponse(data, safe=False)


@login_required
def api_get_tactic_details(request, tactic_id):
    """API endpoint to get details for a specific tactic"""
    tactic = get_object_or_404(MitreTactic, pk=tactic_id)
    
    data = {
        'id': tactic.id,
        'tactic_id': tactic.tactic_id,
        'name': tactic.name,
        'description': tactic.description,
        'url': tactic.url
    }
    
    return JsonResponse(data)


@login_required
def api_get_technique_details(request, technique_id):
    """API endpoint to get details for a specific technique"""
    technique = get_object_or_404(MitreTechnique, pk=technique_id)
    
    # Get related tactics
    tactics = []
    for tactic in technique.tactics.all():
        tactics.append({
            'id': tactic.id,
            'tactic_id': tactic.tactic_id,
            'name': tactic.name
        })
    
    data = {
        'id': technique.id,
        'technique_id': technique.technique_id,
        'name': technique.name,
        'description': technique.description,
        'url': technique.url,
        'tactics': tactics
    }
    
    return JsonResponse(data)


@login_required
def api_get_subtechnique_details(request, subtechnique_id):
    """API endpoint to get details for a specific sub-technique"""
    subtechnique = get_object_or_404(MitreSubTechnique, pk=subtechnique_id)
    
    # Get parent technique info
    parent = None
    if subtechnique.parent_technique:
        parent = {
            'id': subtechnique.parent_technique.id,
            'technique_id': subtechnique.parent_technique.technique_id,
            'name': subtechnique.parent_technique.name
        }
    
    data = {
        'id': subtechnique.id,
        'sub_technique_id': subtechnique.sub_technique_id,
        'name': subtechnique.name,
        'description': subtechnique.description,
        'url': subtechnique.url,
        'parent_technique': parent
    }
    
    return JsonResponse(data)


@login_required
def mitre_attack_group_list(request):
    """List MITRE ATT&CK Groups for the organization"""
    groups = MitreAttackGroup.objects.filter(organization=request.user.organization)
    
    context = {
        'groups': groups,
    }
    
    return render(request, 'core/mitre_attack_group_list.html', context)


@login_required
def mitre_attack_group_create(request):
    """Create a new MITRE ATT&CK Group"""
    if request.method == 'POST':
        form = MitreAttackGroupForm(request.POST, organization=request.user.organization)
        if form.is_valid():
            group = form.save()
            messages.success(request, _('MITRE ATT&CK Group created successfully.'))
            return redirect('mitre_attack_group_detail', group_id=group.id)
    else:
        form = MitreAttackGroupForm(organization=request.user.organization)
    
    context = {
        'form': form,
        'title': _('Create MITRE ATT&CK Group')
    }
    
    return render(request, 'core/mitre_attack_group_form.html', context)


@login_required
def mitre_attack_group_detail(request, group_id):
    """View a MITRE ATT&CK Group"""
    group = get_object_or_404(MitreAttackGroup, id=group_id, organization=request.user.organization)
    
    context = {
        'group': group,
        'tactics': group.tactics.all(),
        'techniques': group.techniques.all(),
        'subtechniques': group.subtechniques.all(),
        'cases': group.cases.all()[:5],
        'alerts': group.alerts.all()[:5],
    }
    
    return render(request, 'core/mitre_attack_group_detail.html', context)


@login_required
def mitre_attack_group_edit(request, group_id):
    """Edit a MITRE ATT&CK Group"""
    group = get_object_or_404(MitreAttackGroup, id=group_id, organization=request.user.organization)
    
    if request.method == 'POST':
        form = MitreAttackGroupForm(request.POST, instance=group, organization=request.user.organization)
        if form.is_valid():
            form.save()
            messages.success(request, _('MITRE ATT&CK Group updated successfully.'))
            return redirect('mitre_attack_group_detail', group_id=group.id)
    else:
        form = MitreAttackGroupForm(instance=group, organization=request.user.organization)
    
    context = {
        'form': form,
        'group': group,
        'title': _('Edit MITRE ATT&CK Group')
    }
    
    return render(request, 'core/mitre_attack_group_form.html', context)


@login_required
def mitre_attack_group_delete(request, group_id):
    """Delete a MITRE ATT&CK Group"""
    group = get_object_or_404(MitreAttackGroup, id=group_id, organization=request.user.organization)
    
    if request.method == 'POST':
        group.delete()
        messages.success(request, _('MITRE ATT&CK Group deleted successfully.'))
        return redirect('mitre_attack_group_list')
    
    context = {
        'group': group,
    }
    
    return render(request, 'core/mitre_attack_group_confirm_delete.html', context)


@login_required
def add_case_mitre_attack_group(request, case_id):
    """Add a MITRE ATT&CK Group to a case"""
    case = get_object_or_404(Case, id=case_id, organization=request.user.organization)
    
    if request.method == 'POST':
        group_id = request.POST.get('group')
        if group_id:
            group = get_object_or_404(MitreAttackGroup, id=group_id, organization=request.user.organization)
            case.mitre_attack_groups.add(group)
            
            # Log the action
            case.add_timeline_event(
                event_type=CaseEvent.MITRE_ATTACK_ADDED,
                title=_('MITRE ATT&CK Group added'),
                description=f"{group.name}",
                user=request.user,
                metadata={'group_id': group.id}
            )
            
            messages.success(request, _('MITRE ATT&CK Group added to case successfully.'))
            return redirect('case_detail', case_id=case.id)
    
    groups = MitreAttackGroup.objects.filter(organization=request.user.organization)
    existing_groups = case.mitre_attack_groups.all()
    available_groups = groups.exclude(id__in=[g.id for g in existing_groups])
    
    context = {
        'case': case,
        'groups': available_groups,
        'existing_groups': existing_groups,
    }
    
    return render(request, 'core/add_case_mitre_attack_group.html', context)


@login_required
def remove_case_mitre_attack_group(request, case_id, group_id):
    """Remove a MITRE ATT&CK Group from a case"""
    case = get_object_or_404(Case, id=case_id, organization=request.user.organization)
    group = get_object_or_404(MitreAttackGroup, id=group_id, organization=request.user.organization)
    
    if request.method == 'POST':
        case.mitre_attack_groups.remove(group)
        
        # Log the action
        case.add_timeline_event(
            event_type=CaseEvent.MITRE_ATTACK_REMOVED,
            title=_('MITRE ATT&CK Group removed'),
            description=f"{group.name}",
            user=request.user,
            metadata={'group_id': group.id}
        )
        
        messages.success(request, _('MITRE ATT&CK Group removed from case successfully.'))
    
    return redirect('case_detail', case_id=case.id)


@login_required
def add_alert_mitre_attack_group(request, alert_id):
    """Add a MITRE ATT&CK Group to an alert"""
    alert = get_object_or_404(Alert, id=alert_id, organization=request.user.organization)
    
    if request.method == 'POST':
        group_id = request.POST.get('group')
        if group_id:
            group = get_object_or_404(MitreAttackGroup, id=group_id, organization=request.user.organization)
            alert.mitre_attack_groups.add(group)
            
            # Log the action
            alert.add_timeline_event(
                event_type=AlertEvent.MITRE_ATTACK_ADDED,
                title=_('MITRE ATT&CK Group added'),
                description=f"{group.name}",
                user=request.user,
                metadata={'group_id': group.id}
            )
            
            messages.success(request, _('MITRE ATT&CK Group added to alert successfully.'))
            return redirect('alert_detail', alert_id=alert.id)
    
    groups = MitreAttackGroup.objects.filter(organization=request.user.organization)
    existing_groups = alert.mitre_attack_groups.all()
    available_groups = groups.exclude(id__in=[g.id for g in existing_groups])
    
    context = {
        'alert': alert,
        'groups': available_groups,
        'existing_groups': existing_groups,
    }
    
    return render(request, 'core/add_alert_mitre_attack_group.html', context)


@login_required
def remove_alert_mitre_attack_group(request, alert_id, group_id):
    """Remove a MITRE ATT&CK Group from an alert"""
    alert = get_object_or_404(Alert, id=alert_id, organization=request.user.organization)
    group = get_object_or_404(MitreAttackGroup, id=group_id, organization=request.user.organization)
    
    if request.method == 'POST':
        alert.mitre_attack_groups.remove(group)
        
        # Log the action
        alert.add_timeline_event(
            event_type=AlertEvent.MITRE_ATTACK_REMOVED,
            title=_('MITRE ATT&CK Group removed'),
            description=f"{group.name}",
            user=request.user,
            metadata={'group_id': group.id}
        )
        
        messages.success(request, _('MITRE ATT&CK Group removed from alert successfully.'))
    
    return redirect('alert_detail', alert_id=alert.id)


@login_required
def api_get_techniques_by_multiple_tactics(request):
    """API endpoint to get techniques for multiple tactics"""
    tactic_ids = request.GET.get('tactics', '').split(',')
    tactics = MitreTactic.objects.filter(id__in=tactic_ids)
    
    # Buscar técnicas associadas a qualquer uma das táticas especificadas
    techniques = MitreTechnique.objects.filter(tactics__in=tactics).distinct()
    
    data = []
    for technique in techniques:
        data.append({
            'id': technique.id,
            'technique_id': technique.technique_id,
            'name': technique.name,
            'description': technique.description,
            'url': technique.url
        })
    
    return JsonResponse(data, safe=False)


@login_required
def api_get_subtechniques_by_multiple_techniques(request):
    """API endpoint to get subtechniques for multiple techniques"""
    try:
        technique_ids = request.GET.get('techniques', '').split(',')
        technique_ids = [tid for tid in technique_ids if tid.strip()]  # Remove valores vazios
        
        if not technique_ids:
            return JsonResponse([], safe=False)
            
        techniques = MitreTechnique.objects.filter(id__in=technique_ids)
        
        # Buscar subtécnicas associadas a qualquer uma das técnicas especificadas
        subtechniques = MitreSubTechnique.objects.filter(parent_technique__in=techniques).order_by('sub_technique_id')
        
        data = []
        for subtechnique in subtechniques:
            data.append({
                'id': subtechnique.id,
                'sub_technique_id': subtechnique.sub_technique_id,
                'name': subtechnique.name,
                'description': subtechnique.description,
                'url': subtechnique.url,
                'parent_technique_id': subtechnique.parent_technique.id
            })
        
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
