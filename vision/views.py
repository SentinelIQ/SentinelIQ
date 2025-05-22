from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse
from django.utils import timezone
from django.db import models
from django.views.decorators.http import require_POST
import logging

from .models import ThreatIntelligenceFeed, MISPInstance, ThreatIntelligenceItem
from .forms import MISPInstanceForm, ThreatIntelligenceSearchForm
from .services.misp import MISPService
from .services.misp_case_integration import MISPCaseIntegration


class FeedListView(LoginRequiredMixin, ListView):
    model = ThreatIntelligenceFeed
    context_object_name = 'feeds'
    template_name = 'vision/feed_list.html'
    
    def get_queryset(self):
        # Mostrar feeds públicos ou feeds da organização do usuário
        organization = self.request.user.organization
        return ThreatIntelligenceFeed.objects.filter(
            models.Q(is_public=True) | models.Q(organization=organization)
        )


class MISPInstanceCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = MISPInstance
    form_class = MISPInstanceForm
    template_name = 'vision/misp_form.html'
    success_url = reverse_lazy('vision:feed_list')
    
    def test_func(self):
        # Apenas usuários administradores podem criar instâncias MISP
        return self.request.user.is_staff or self.request.user.is_organization_admin
    
    def form_valid(self, form):
        form.instance.feed_type = 'misp'
        form.instance.organization = self.request.user.organization
        messages.success(self.request, _('MISP instance created successfully.'))
        return super().form_valid(form)


class MISPInstanceUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = MISPInstance
    form_class = MISPInstanceForm
    template_name = 'vision/misp_form.html'
    success_url = reverse_lazy('vision:feed_list')
    
    def test_func(self):
        # Apenas administradores ou usuários da mesma organização podem editar
        obj = self.get_object()
        return (self.request.user.is_staff or 
                self.request.user.is_organization_admin and 
                obj.organization == self.request.user.organization)
    
    def form_valid(self, form):
        messages.success(self.request, _('MISP instance updated successfully.'))
        return super().form_valid(form)


class MISPInstanceDetailView(LoginRequiredMixin, DetailView):
    model = MISPInstance
    template_name = 'vision/misp_detail.html'
    context_object_name = 'misp'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Adicionar dados dos últimos itens obtidos deste feed
        context['recent_items'] = ThreatIntelligenceItem.objects.filter(
            feed=self.object
        ).order_by('-created_at')[:20]
        return context


@login_required
def sync_misp_instance(request, pk):
    """Endpoint para sincronizar manualmente uma instância MISP"""
    misp = get_object_or_404(MISPInstance, pk=pk)
    
    # Verificar permissões
    if not (request.user.is_staff or 
            request.user.is_organization_admin and 
            misp.organization == request.user.organization):
        messages.error(request, _("You don't have permission to sync this feed."))
        return redirect('vision:feed_list')
    
    try:
        service = MISPService(misp)
        items_imported = service.sync()
        
        # Atualizar timestamp de sincronização
        misp.last_sync = timezone.now()
        misp.status = 'active'
        misp.save()
        
        messages.success(
            request, 
            _('Successfully synchronized MISP instance "%(name)s". %(count)d items imported/updated.') % {
                'name': misp.name,
                'count': items_imported
            }
        )
    except Exception as e:
        misp.status = 'error'
        misp.save()
        messages.error(
            request,
            _('Error synchronizing MISP instance "%(name)s": %(error)s') % {
                'name': misp.name,
                'error': str(e)
            }
        )
    
    return redirect('vision:misp_detail', pk=misp.pk)


class ThreatIntelligenceSearchView(LoginRequiredMixin, ListView):
    """View para busca de indicadores de ameaças"""
    model = ThreatIntelligenceItem
    template_name = 'vision/search.html'
    context_object_name = 'items'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = ThreatIntelligenceItem.objects.all()
        
        # Filtrar por organização do usuário ou feeds públicos
        organization = self.request.user.organization
        queryset = queryset.filter(
            models.Q(feed__is_public=True) | models.Q(feed__organization=organization)
        )
        
        # Aplicar filtros adicionais com base no formulário
        form = ThreatIntelligenceSearchForm(self.request.GET)
        if form.is_valid():
            if form.cleaned_data.get('search_term'):
                queryset = queryset.filter(value__icontains=form.cleaned_data['search_term'])
            
            if form.cleaned_data.get('item_type'):
                queryset = queryset.filter(item_type=form.cleaned_data['item_type'])
            
            if form.cleaned_data.get('confidence'):
                queryset = queryset.filter(confidence=form.cleaned_data['confidence'])
            
            if form.cleaned_data.get('is_malicious') is not None:
                queryset = queryset.filter(is_malicious=form.cleaned_data['is_malicious'])
            
            if form.cleaned_data.get('tlp'):
                queryset = queryset.filter(tlp=form.cleaned_data['tlp'])
                
            if form.cleaned_data.get('creator_org'):
                queryset = queryset.filter(creator_org__icontains=form.cleaned_data['creator_org'])
        
        return queryset.order_by('-last_seen')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ThreatIntelligenceSearchForm(self.request.GET)
        return context


@login_required
@require_POST
def test_misp_connection(request):
    """Endpoint para testar a conexão com uma instância MISP sem salvá-la"""
    try:
        # Obter os dados do formulário
        url = request.POST.get('url')
        api_key = request.POST.get('api_key')
        verify_ssl = request.POST.get('verify_ssl') == 'true'
        
        if not url or not api_key:
            return JsonResponse({
                'success': False,
                'message': _('URL and API key are required.')
            }, status=400)
        
        # Criar uma instância temporária do MISP
        temp_misp = MISPInstance(
            url=url,
            api_key=api_key,
            verify_ssl=verify_ssl,
            name="Temporary Instance",
            feed_type="misp",
            organization=request.user.organization
        )
        
        # Testar a conexão
        service = MISPService(temp_misp)
        
        # Tentar fazer uma requisição simples para verificar a conexão
        response = service._request('/servers/getVersion')
        
        # Log the response structure to help debug
        logger = logging.getLogger(__name__)
        logger.info(f"MISP test connection response type: {type(response)}")
        
        version = "Unknown"
        # Handle different response structures
        if isinstance(response, dict):
            version = response.get('version', 'Unknown')
        elif isinstance(response, list) and response:
            if isinstance(response[0], dict):
                version = response[0].get('version', 'Unknown')
        
        # Se chegou até aqui, a conexão foi bem sucedida
        return JsonResponse({
            'success': True,
            'message': _('Connection successful! MISP version: {}').format(version),
            'version': version
        })
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"MISP connection test failed: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': _('Connection failed: {}').format(str(e))
        }, status=400)


class MISPInstanceDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = MISPInstance
    template_name = 'vision/misp_confirm_delete.html'
    success_url = reverse_lazy('vision:feed_list')
    
    def test_func(self):
        # Apenas administradores ou usuários da mesma organização podem excluir
        obj = self.get_object()
        return (self.request.user.is_staff or 
                self.request.user.is_organization_admin and 
                obj.organization == self.request.user.organization)
    
    def delete(self, request, *args, **kwargs):
        misp_instance = self.get_object()
        messages.success(
            request, 
            _('MISP Instance "%(name)s" was successfully deleted.') % {'name': misp_instance.name}
        )
        return super().delete(request, *args, **kwargs)


@login_required
@require_POST
def create_case_from_threat_intel(request, pk):
    """Create a new case from a threat intelligence item"""
    # Get the threat intelligence item
    intel_item = get_object_or_404(ThreatIntelligenceItem, pk=pk)
    
    # Check if user has access to this intel item
    user_org = request.user.organization
    if not (intel_item.feed.is_public or intel_item.feed.organization == user_org):
        messages.error(request, _("You don't have access to this threat intelligence item."))
        return redirect('vision:search')
    
    try:
        # Create a new case
        case = MISPCaseIntegration.create_case_from_threat_intel(
            threat_intel_item=intel_item,
            organization=user_org,
            user=request.user,
            title=request.POST.get('title')
        )
        
        messages.success(
            request,
            _('Case "{title}" successfully created from threat intelligence item.').format(title=case.title)
        )
        
        # Redirect to the new case
        return redirect('cases:case_detail', pk=case.id)
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error creating case from threat intelligence: {str(e)}", exc_info=True)
        
        messages.error(
            request,
            _('Failed to create case from threat intelligence: {error}').format(error=str(e))
        )
        
        # Redirect back to the threat intel search
        return redirect('vision:search')


@login_required
@require_POST
def enrich_case_with_threat_intel(request, case_pk):
    """Enrich an existing case with threat intelligence data for all its observables"""
    from cases.models import Case
    
    # Get the case
    case = get_object_or_404(Case, pk=case_pk)
    
    # Check if user has access to this case
    user_org = request.user.organization
    if case.organization != user_org:
        messages.error(request, _("You don't have access to this case."))
        return redirect('cases:case_list')
    
    try:
        # Enrich the case with threat intelligence
        stats = MISPCaseIntegration.enrich_case_with_threat_intel(case)
        
        if stats['observables_enriched'] > 0:
            messages.success(
                request,
                _('Successfully enriched {count} observables with threat intelligence data.').format(
                    count=stats['observables_enriched']
                )
            )
        else:
            messages.info(
                request,
                _('No matching threat intelligence found for observables in this case.')
            )
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error enriching case with threat intelligence: {str(e)}", exc_info=True)
        
        messages.error(
            request,
            _('Failed to enrich case with threat intelligence: {error}').format(error=str(e))
        )
    
    # Redirect back to the case
    return redirect('cases:case_detail', pk=case_pk)
    

@login_required
def threat_intel_match(request, observable_pk):
    """Check if an observable matches any threat intelligence items"""
    from core.models import Observable
    
    # Get the observable
    observable = get_object_or_404(Observable, pk=observable_pk)
    
    # Check if user has access to this observable
    user_org = request.user.organization
    if observable.organization != user_org:
        return JsonResponse({
            'success': False,
            'error': str(_("You don't have access to this observable."))
        }, status=403)
    
    try:
        # Find matching threat intelligence
        items = MISPCaseIntegration.find_threat_intel_for_observable(observable)
        
        # Format the response
        items_data = []
        for item in items:
            items_data.append({
                'id': item.id,
                'value': item.value,
                'type': item.get_item_type_display(),
                'is_malicious': item.is_malicious,
                'confidence': item.confidence,
                'tlp': item.tlp,
                'feed_name': item.feed.name,
                'creator_org': item.creator_org,
                'tags': item.tags,
                'external_url': item.external_url,
                'description': item.description[:200] + ('...' if len(item.description) > 200 else '')
            })
        
        return JsonResponse({
            'success': True,
            'observable': {
                'id': observable.id,
                'value': observable.value,
                'type': observable.get_type_display()
            },
            'matches': items_data,
            'count': len(items_data)
        })
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error checking threat intel match: {str(e)}", exc_info=True)
        
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500) 