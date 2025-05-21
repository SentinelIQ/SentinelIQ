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

from accounts.views import OrgAdminRequiredMixin
from .models import Tag, Observable
from .forms import TagForm, ObservableForm, ObservableFilterForm
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
        form = ObservableForm(request.POST)
        if form.is_valid():
            try:
                observable = form.save()
                messages.success(request, 'Observable criado com sucesso!')
                
                # Optional: Redirect based on where the user came from
                if 'alert_id' in request.GET:
                    alert_id = request.GET.get('alert_id')
                    alert = get_object_or_404(Alert, pk=alert_id)
                    alert.observables.add(observable)
                    alert.log_observable_added(request.user, observable)
                    return redirect('alert_detail', alert_id)
                elif 'case_id' in request.GET:
                    case_id = request.GET.get('case_id')
                    case = get_object_or_404(Case, pk=case_id)
                    case.observables.add(observable)
                    case.log_observable_added(request.user, observable)
                    return redirect('case_detail', case_id)
                
                return redirect('observable_list')
            except IntegrityError:
                form.add_error(None, 'Este valor de observable já existe com este tipo. Os observables devem ser únicos por tipo e valor.')
    else:
        form = ObservableForm()
    
    context = {
        'form': form,
        'title': 'Criar Novo Observable'
    }
    
    return render(request, 'core/observable_form.html', context)


@login_required
def observable_update(request, pk):
    """Update an existing observable"""
    observable = get_object_or_404(Observable, pk=pk)
    
    if request.method == 'POST':
        form = ObservableForm(request.POST, instance=observable)
        if form.is_valid():
            form.save()
            messages.success(request, 'Observable atualizado com sucesso!')
            return redirect('observable_detail', pk=observable.pk)
    else:
        form = ObservableForm(instance=observable)
    
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
