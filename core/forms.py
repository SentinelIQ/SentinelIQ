from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Tag, Observable, MitreTactic, MitreTechnique, MitreSubTechnique, MitreAttackGroup
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
    """Form for creating and updating observables"""
    
    # Campos para associar o observable a alertas e casos
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
    
    class Meta:
        model = Observable
        fields = (
            'value', 'type', 'confidence', 'is_malicious', 'pap', 'description'
        )
        widgets = {
            'value': forms.TextInput(attrs={'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-select'}),
            'confidence': forms.Select(attrs={'class': 'form-select'}),
            'is_malicious': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'pap': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
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
    
    def clean(self):
        cleaned_data = super().clean()
        value = cleaned_data.get('value')
        ioc_type = cleaned_data.get('type')
        
        # Add validation logic based on the type of IOC
        if value and ioc_type:
            if ioc_type == Observable.IP:
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
    """Form for filtering observables"""
    type = forms.ChoiceField(
        choices=[('', _('All Types'))] + Observable.TYPE_CHOICES,
        required=False,
        label=_('Type'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    is_malicious = forms.ChoiceField(
        choices=[
            ('', _('All')),
            ('true', _('Malicious')),
            ('false', _('Not Malicious')),
        ],
        required=False,
        label=_('Malicious'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    confidence = forms.ChoiceField(
        choices=[('', _('All Confidence'))] + Observable.CONFIDENCE_CHOICES,
        required=False,
        label=_('Confidence'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    search = forms.CharField(
        required=False,
        label=_('Search'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Search by value or description')
        })
    )


class MitreTacticForm(forms.ModelForm):
    """Form for MITRE ATT&CK Tactics"""
    class Meta:
        model = MitreTactic
        fields = ['tactic_id', 'name', 'description', 'url']
        widgets = {
            'tactic_id': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'url': forms.URLInput(attrs={'class': 'form-control'}),
        }


class MitreTechniqueForm(forms.ModelForm):
    """Form for MITRE ATT&CK Techniques"""
    class Meta:
        model = MitreTechnique
        fields = ['technique_id', 'name', 'description', 'url', 'tactics']
        widgets = {
            'technique_id': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'url': forms.URLInput(attrs={'class': 'form-control'}),
            'tactics': forms.SelectMultiple(attrs={'class': 'form-select'}),
        }


class MitreSubTechniqueForm(forms.ModelForm):
    """Form for MITRE ATT&CK Sub-techniques"""
    class Meta:
        model = MitreSubTechnique
        fields = ['sub_technique_id', 'name', 'description', 'url', 'parent_technique']
        widgets = {
            'sub_technique_id': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'url': forms.URLInput(attrs={'class': 'form-control'}),
            'parent_technique': forms.Select(attrs={'class': 'form-select'}),
        }


class MitreAttackSelectionForm(forms.Form):
    """Form for selecting MITRE ATT&CK elements to add to alerts or cases"""
    tactic = forms.ModelChoiceField(
        queryset=MitreTactic.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label=_('Select a Tactic')
    )
    
    technique = forms.ModelChoiceField(
        queryset=MitreTechnique.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label=_('Select a Technique')
    )
    
    subtechnique = forms.ModelChoiceField(
        queryset=MitreSubTechnique.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label=_('Select a Sub-technique (optional)')
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If initial tactic is provided, filter techniques accordingly
        if 'tactic' in self.initial:
            tactic = self.initial['tactic']
            self.fields['technique'].queryset = MitreTechnique.objects.filter(tactics=tactic)
        
        # If initial technique is provided, filter sub-techniques accordingly
        if 'technique' in self.initial:
            technique = self.initial['technique']
            self.fields['subtechnique'].queryset = MitreSubTechnique.objects.filter(parent_technique=technique)


class MitreAttackGroupForm(forms.ModelForm):
    """Form for creating and editing MITRE ATT&CK Groups"""
    class Meta:
        model = MitreAttackGroup
        fields = ['name', 'description', 'tactics', 'techniques', 'subtechniques']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'tactics': forms.SelectMultiple(attrs={'class': 'form-select', 'size': '5'}),
            'techniques': forms.SelectMultiple(attrs={'class': 'form-select', 'size': '5'}),
            'subtechniques': forms.SelectMultiple(attrs={'class': 'form-select', 'size': '5'}),
        }
        
    def __init__(self, *args, **kwargs):
        organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)
        
        if organization:
            self.instance.organization = organization 