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
from alerts.models import Alert
from cases.models import Case
from core.models import Observable


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
        context['alerts_count'] = Alert.objects.count()  # Total de alertas para superadmin
        context['cases_count'] = Case.objects.count()  # Total de casos para superadmin
        context['observables_count'] = Observable.objects.count()  # Total de observables para superadmin
        context['recent_organizations'] = Organization.objects.all().order_by('-created_at')[:5]  # 5 organizações mais recentes
        return render(request, 'accounts/dashboard_superadmin.html', context)
    elif request.user.is_org_admin():
        # Organization admin dashboard
        org = request.user.organization
        alerts = org.alerts.all()
        cases = org.cases.all()
        context['alerts_count'] = alerts.count()
        context['users_count'] = org.users.count()
        context['cases_count'] = cases.count()  # Total de casos da organização
        context['new_alerts_count'] = alerts.filter(status='new').count()
        context['resolved_alerts_count'] = alerts.filter(status='resolved').count()
        context['recent_alerts'] = alerts.order_by('-created_at')[:5]  # 5 alertas mais recentes
        
        # Obtendo observables associados aos alertas da organização
        alert_observable_ids = alerts.values_list('observables', flat=True)
        # Obtendo observables associados aos casos da organização
        case_observable_ids = cases.values_list('observables', flat=True)
        # Combinando os IDs únicos
        unique_observable_ids = set(list(alert_observable_ids) + list(case_observable_ids))
        # Removendo None se existir
        unique_observable_ids = {id for id in unique_observable_ids if id is not None}
        context['observables_count'] = len(unique_observable_ids)
        
        return render(request, 'accounts/dashboard_org_admin.html', context)
    else:
        # Analyst dashboard
        assigned_alerts = request.user.assigned_alerts.all()
        assigned_cases = request.user.assigned_cases.all()
        
        context['assigned_alerts'] = assigned_alerts[:5]
        context['alerts_count'] = assigned_alerts.count()  # Total de alertas atribuídos ao analista
        context['assigned_cases'] = assigned_cases[:5]  # Casos atribuídos ao analista
        context['cases_count'] = assigned_cases.count()  # Total de casos atribuídos ao analista
        
        # Obtendo observables associados aos alertas do analista
        alert_observable_ids = assigned_alerts.values_list('observables', flat=True)
        # Obtendo observables associados aos casos do analista
        case_observable_ids = assigned_cases.values_list('observables', flat=True)
        # Combinando os IDs únicos
        unique_observable_ids = set(list(alert_observable_ids) + list(case_observable_ids))
        # Removendo None se existir
        unique_observable_ids = {id for id in unique_observable_ids if id is not None}
        context['observables_count'] = len(unique_observable_ids)
        
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
