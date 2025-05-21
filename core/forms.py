from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Tag


class TagForm(forms.ModelForm):
    """Form for creating and updating tags"""
    
    COLOR_CHOICES = [
        ('primary', _('Blue (Primary)')),
        ('secondary', _('Gray (Secondary)')),
        ('success', _('Green (Success)')),
        ('danger', _('Red (Danger)')),
        ('warning', _('Yellow (Warning)')),
        ('info', _('Cyan (Info)')),
        ('dark', _('Black (Dark)')),
        ('purple', _('Purple')),
        ('pink', _('Pink')),
        ('orange', _('Orange')),
        ('teal', _('Teal')),
        ('indigo', _('Indigo'))
    ]
    
    color = forms.ChoiceField(
        choices=COLOR_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = Tag
        fields = ('name', 'color')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        } 