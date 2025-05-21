from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.utils.translation import gettext_lazy as _

from accounts.views import OrgAdminRequiredMixin
from .models import Tag
from .forms import TagForm


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
    
    def form_valid(self, form):
        messages.success(self.request, _('Tag created successfully.'))
        return super().form_valid(form)


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
