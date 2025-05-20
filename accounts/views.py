from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, FormView
from django.utils.translation import gettext_lazy as _

from .models import User
from .forms import CustomUserCreationForm, CustomUserChangeForm, CustomAuthenticationForm
from organizations.models import Organization


def login_view(request):
    """Login view for users"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('dashboard')
            else:
                messages.error(request, _('Invalid username or password.'))
        else:
            messages.error(request, _('Invalid username or password.'))
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """Logout view for users"""
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    """Dashboard view for users"""
    context = {
        'title': _('Dashboard'),
    }
    if request.user.is_superadmin():
        # Super admin dashboard
        context['organizations_count'] = Organization.objects.count()
        context['users_count'] = User.objects.count()
        return render(request, 'accounts/dashboard_superadmin.html', context)
    elif request.user.is_org_admin():
        # Organization admin dashboard
        org = request.user.organization
        context['alerts_count'] = org.alerts.count()
        context['users_count'] = org.users.count()
        return render(request, 'accounts/dashboard_org_admin.html', context)
    else:
        # Analyst dashboard
        context['assigned_alerts'] = request.user.assigned_alerts.all()[:5]
        return render(request, 'accounts/dashboard_analyst.html', context)


class SuperAdminRequiredMixin(UserPassesTestMixin):
    """Mixin to ensure only superadmins can access a view"""
    def test_func(self):
        return self.request.user.is_superadmin()


class OrgAdminRequiredMixin(UserPassesTestMixin):
    """Mixin to ensure only org admins or superadmins can access a view"""
    def test_func(self):
        return self.request.user.is_org_admin() or self.request.user.is_superadmin()


class UserListView(LoginRequiredMixin, OrgAdminRequiredMixin, ListView):
    """List view for users"""
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    
    def get_queryset(self):
        if self.request.user.is_superadmin():
            return User.objects.all()
        else:
            return User.objects.filter(organization=self.request.user.organization)


class UserDetailView(LoginRequiredMixin, OrgAdminRequiredMixin, DetailView):
    """Detail view for users"""
    model = User
    template_name = 'accounts/user_detail.html'
    context_object_name = 'user_obj'
    
    def get_queryset(self):
        if self.request.user.is_superadmin():
            return User.objects.all()
        else:
            return User.objects.filter(organization=self.request.user.organization)


class UserCreateView(LoginRequiredMixin, OrgAdminRequiredMixin, CreateView):
    """Create view for users"""
    model = User
    form_class = CustomUserCreationForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('user_list')
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        
        # Limit organization choices for org admin
        if not self.request.user.is_superadmin():
            form.fields['organization'].queryset = form.fields['organization'].queryset.filter(id=self.request.user.organization.id)
            form.fields['organization'].initial = self.request.user.organization
            form.fields['organization'].disabled = True
            
            # Limit role choices for org admin
            form.fields['role'].choices = [
                choice for choice in form.fields['role'].choices 
                if choice[0] != User.SUPERADMIN
            ]
        
        return form
    
    def form_valid(self, form):
        messages.success(self.request, _('User created successfully.'))
        return super().form_valid(form)


class UserUpdateView(LoginRequiredMixin, OrgAdminRequiredMixin, UpdateView):
    """Update view for users"""
    model = User
    form_class = CustomUserChangeForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('user_list')
    
    def get_queryset(self):
        if self.request.user.is_superadmin():
            return User.objects.all()
        else:
            return User.objects.filter(organization=self.request.user.organization)
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        
        # Limit organization choices for org admin
        if not self.request.user.is_superadmin():
            form.fields['organization'].queryset = form.fields['organization'].queryset.filter(id=self.request.user.organization.id)
            form.fields['organization'].disabled = True
            
            # Limit role choices for org admin
            form.fields['role'].choices = [
                choice for choice in form.fields['role'].choices 
                if choice[0] != User.SUPERADMIN
            ]
            
            # Prevent org admin from editing superadmin
            if self.object.is_superadmin():
                for field in form.fields.values():
                    field.disabled = True
        
        return form
    
    def form_valid(self, form):
        messages.success(self.request, _('User updated successfully.'))
        return super().form_valid(form)
