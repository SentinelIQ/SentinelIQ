from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
from .models import Organization


class OrganizationForm(forms.ModelForm):
    """Form for creating and updating organizations"""
    
    class Meta:
        model = Organization
        fields = ('name', 'description', 'is_active')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.slug:
            instance.slug = slugify(instance.name)
        
        if commit:
            instance.save()
        return instance 