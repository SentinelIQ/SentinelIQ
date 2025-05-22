from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.utils.translation import gettext_lazy as _

from accounts.views import SuperAdminRequiredMixin
from .models import Organization
from .forms import OrganizationForm


class OrganizationListView(LoginRequiredMixin, SuperAdminRequiredMixin, ListView):
    """List view for organizations"""
    model = Organization
    template_name = 'organizations/organization_list.html'
    context_object_name = 'organizations'


class OrganizationDetailView(LoginRequiredMixin, SuperAdminRequiredMixin, DetailView):
    """Detail view for organizations"""
    model = Organization
    template_name = 'organizations/organization_detail.html'
    context_object_name = 'organization'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_object()
        users = organization.users.all()
        context['users'] = users
        context['users_count'] = users.count()
        context['admins_count'] = users.filter(role='org_admin').count()
        alerts = organization.alerts.all()
        context['alerts'] = alerts[:5]  # Only first 5 for display
        context['alerts_count'] = alerts.count()
        return context


class OrganizationCreateView(LoginRequiredMixin, SuperAdminRequiredMixin, CreateView):
    """Create view for organizations"""
    model = Organization
    form_class = OrganizationForm
    template_name = 'organizations/organization_form.html'
    success_url = reverse_lazy('organizations:organization_list')
    
    def form_valid(self, form):
        messages.success(self.request, _('Organization created successfully.'))
        return super().form_valid(form)


class OrganizationUpdateView(LoginRequiredMixin, SuperAdminRequiredMixin, UpdateView):
    """Update view for organizations"""
    model = Organization
    form_class = OrganizationForm
    template_name = 'organizations/organization_form.html'
    success_url = reverse_lazy('organizations:organization_list')
    
    def form_valid(self, form):
        messages.success(self.request, _('Organization updated successfully.'))
        return super().form_valid(form)


class OrganizationDeleteView(LoginRequiredMixin, SuperAdminRequiredMixin, DeleteView):
    """Delete view for organizations"""
    model = Organization
    template_name = 'organizations/organization_confirm_delete.html'
    success_url = reverse_lazy('organizations:organization_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_object()
        users = organization.users.all()
        context['users_count'] = users.count()
        alerts = organization.alerts.all()
        context['alerts_count'] = alerts.count()
        # For demonstration purposes - this could be actual related data count
        context['other_data_count'] = 0
        return context
    
    def delete(self, request, *args, **kwargs):
        organization = self.get_object()
        messages.success(request, _(f'Organization "{organization.name}" was deleted successfully.'))
        return super().delete(request, *args, **kwargs)
