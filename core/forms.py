from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Tag, Observable
from alerts.models import Alert
from cases.models import Case


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
    
    # Novos campos para associar a tag a alertas e casos
    alert = forms.ModelChoiceField(
        queryset=Alert.objects.all(),
        required=False,
        empty_label="-- Selecione um alerta (opcional) --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    case = forms.ModelChoiceField(
        queryset=Case.objects.all(),
        required=False,
        empty_label="-- Selecione um caso (opcional) --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    color = forms.ChoiceField(
        choices=COLOR_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = Tag
        fields = ('name', 'color', 'alert', 'case')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        # Pegar o usuário atual da view para filtrar alertas e casos
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            # Filtrar alertas e casos pela organização do usuário
            self.fields['alert'].queryset = Alert.objects.filter(
                organization=user.organization
            ).order_by('-created_at')
            
            self.fields['case'].queryset = Case.objects.filter(
                organization=user.organization
            ).order_by('-created_at')
            
            # Adicionar títulos como descrições nos dropdowns
            self.fields['alert'].label_from_instance = lambda obj: f"{obj.title} (ID: {obj.id})"
            self.fields['case'].label_from_instance = lambda obj: f"{obj.title} (ID: {obj.id})"


class ObservableForm(forms.ModelForm):
    class Meta:
        model = Observable
        fields = ['value', 'type', 'description', 'confidence', 'is_malicious']
        widgets = {
            'value': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Valor do IOC'}),
            'type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descrição opcional'}),
            'confidence': forms.Select(attrs={'class': 'form-select'}),
            'is_malicious': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        value = cleaned_data.get('value')
        ioc_type = cleaned_data.get('type')
        
        # Add validation logic based on the type of IOC
        if value and ioc_type:
            if ioc_type == Observable.IP_ADDRESS:
                # Basic IP address validation
                import re
                ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}(\/\d{1,2})?$'
                if not re.match(ip_pattern, value):
                    self.add_error('value', 'Formato de endereço IP inválido.')
            
            elif ioc_type == Observable.EMAIL:
                # Basic email validation
                import re
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, value):
                    self.add_error('value', 'Formato de email inválido.')
            
            elif ioc_type in [Observable.HASH_MD5, Observable.HASH_SHA1, Observable.HASH_SHA256]:
                # Validate hash length based on type
                hash_lengths = {
                    Observable.HASH_MD5: 32,
                    Observable.HASH_SHA1: 40,
                    Observable.HASH_SHA256: 64
                }
                expected_length = hash_lengths.get(ioc_type)
                if expected_length and len(value) != expected_length:
                    self.add_error('value', f'Hash deve ter {expected_length} caracteres.')
        
        return cleaned_data


class ObservableFilterForm(forms.Form):
    type = forms.ChoiceField(
        choices=[('', '-- Todos os tipos --')] + Observable.TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Buscar pelo valor...'})
    )
    is_malicious = forms.ChoiceField(
        choices=[
            ('', '-- Todos --'),
            ('true', 'Malicioso'),
            ('false', 'Não Malicioso')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    confidence = forms.ChoiceField(
        choices=[('', '-- Todos --')] + Observable.CONFIDENCE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    ) 