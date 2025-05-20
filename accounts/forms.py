from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from django.utils.translation import gettext_lazy as _
from .models import User


class CustomUserCreationForm(UserCreationForm):
    """Form for creating new users"""
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'organization', 'role')


class CustomUserChangeForm(UserChangeForm):
    """Form for updating users"""
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'organization', 'role')


class CustomAuthenticationForm(AuthenticationForm):
    """Custom login form with styling"""
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-lg',
                'placeholder': _('Username'),
            }
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control form-control-lg',
                'placeholder': _('Password'),
            }
        )
    ) 