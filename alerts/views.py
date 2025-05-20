from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.utils.translation import gettext_lazy as _
from django.db.models import Q

from accounts.views import OrgAdminRequiredMixin
from .models import Alert
from .forms import AlertForm, AlertFilterForm


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
        messages.success(self.request, _('Alert created successfully.'))
        return super().form_valid(form)


class AlertUpdateView(LoginRequiredMixin, UpdateView):
    """Update view for alerts"""
    model = Alert
    form_class = AlertForm
    template_name = 'alerts/alert_form.html'
    success_url = reverse_lazy('alert_list')
    
    def get_queryset(self):
        """Ensure users can only update alerts from their organization"""
        user = self.request.user
        if user.is_superadmin():
            return Alert.objects.all()
        else:
            return Alert.objects.filter(organization=user.organization)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization'] = self.request.user.organization
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, _('Alert updated successfully.'))
        return super().form_valid(form)


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
