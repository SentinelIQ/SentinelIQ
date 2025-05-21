from django import forms
from django.utils.translation import gettext_lazy as _
from django.forms import ValidationError
import json

from .models import Alert, AlertCustomField, AlertCustomValue


class AlertForm(forms.ModelForm):
    """Form for creating and updating alerts"""
    
    class Meta:
        model = Alert
        fields = ('title', 'description', 'severity', 'status', 'assigned_to', 'tlp', 'pap', 'tags')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'severity': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'tlp': forms.Select(attrs={'class': 'form-select'}),
            'pap': forms.Select(attrs={'class': 'form-select'}),
            'tags': forms.SelectMultiple(attrs={'class': 'form-select', 'size': '5'}),
        }
    
    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields['assigned_to'].queryset = organization.users.all()


class AlertFilterForm(forms.Form):
    """Form for filtering alerts"""
    STATUS_CHOICES = [('', _('All Statuses'))] + list(Alert.STATUS_CHOICES)
    SEVERITY_CHOICES = [('', _('All Severities'))] + list(Alert.SEVERITY_CHOICES)
    TLP_CHOICES = [('', _('All TLP'))] + list(Alert.TLP_CHOICES)
    PAP_CHOICES = [('', _('All PAP'))] + list(Alert.PAP_CHOICES)
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES, 
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    severity = forms.ChoiceField(
        choices=SEVERITY_CHOICES, 
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    tlp = forms.ChoiceField(
        choices=TLP_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    pap = forms.ChoiceField(
        choices=PAP_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    tag = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label=_('All Tags'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Search by title or description')
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from core.models import Tag
        self.fields['tag'].queryset = Tag.objects.all() 


class AlertCustomFieldForm(forms.ModelForm):
    """Form for creating and updating custom fields for alerts"""
    options = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        help_text=_('Enter one option per line (for select field type)')
    )
    
    class Meta:
        model = AlertCustomField
        fields = [
            'name', 'label', 'field_type', 'required', 'description',
            'placeholder', 'default_value', 'options', 'order'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'label': forms.TextInput(attrs={'class': 'form-control'}),
            'field_type': forms.Select(attrs={'class': 'form-select'}),
            'required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'placeholder': forms.TextInput(attrs={'class': 'form-control'}),
            'default_value': forms.TextInput(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set initial value for options as newline-separated string if exists
        if self.instance.pk and self.instance.options:
            try:
                self.initial['options'] = '\n'.join(self.instance.options)
            except (TypeError, ValueError):
                self.initial['options'] = ''
    
    def clean_name(self):
        # Convert to slug-like format (lowercase, underscore)
        name = self.cleaned_data['name'].lower().replace(' ', '_')
        return name
    
    def clean_options(self):
        options = self.cleaned_data['options']
        field_type = self.cleaned_data.get('field_type')
        
        if field_type == AlertCustomField.SELECT and not options:
            raise ValidationError(_('Options are required for select field type'))
        
        if options:
            # Convert newline-separated string to list
            options_list = [opt.strip() for opt in options.split('\n') if opt.strip()]
            return options_list
        
        return None
        
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Save options as JSON list
        options = self.cleaned_data.get('options')
        if options:
            instance.options = options
        
        if commit:
            instance.save()
        
        return instance

class DynamicAlertCustomFieldsForm(forms.Form):
    """Form for custom fields on alerts"""
    
    def __init__(self, *args, organization=None, instance=None, **kwargs):
        self.organization = organization
        self.instance = instance
        super().__init__(*args, **kwargs)
        
        if not organization:
            return
        
        # Get custom fields for this organization
        custom_fields = AlertCustomField.objects.filter(organization=organization).order_by('order')
        
        # Get existing values if we have an instance
        existing_values = {}
        if instance:
            for value in instance.custom_values.select_related('field').all():
                existing_values[value.field.name] = value.value
        
        # Add a field for each custom field
        for field in custom_fields:
            field_name = f"custom_{field.name}"
            field_kwargs = {
                'label': field.label,
                'required': field.required,
                'help_text': field.description,
                'initial': existing_values.get(field.name, field.default_value),
            }
            
            if field.placeholder:
                field_kwargs['widget'] = forms.TextInput(attrs={'placeholder': field.placeholder})
            
            # Create different field types based on the custom field type
            if field.field_type == AlertCustomField.TEXT:
                self.fields[field_name] = forms.CharField(**field_kwargs)
            elif field.field_type == AlertCustomField.NUMBER:
                self.fields[field_name] = forms.FloatField(**field_kwargs)
            elif field.field_type == AlertCustomField.DATE:
                self.fields[field_name] = forms.DateField(**field_kwargs)
            elif field.field_type == AlertCustomField.BOOLEAN:
                self.fields[field_name] = forms.BooleanField(**{**field_kwargs, 'required': False})
            elif field.field_type == AlertCustomField.URL:
                self.fields[field_name] = forms.URLField(**field_kwargs)
            elif field.field_type == AlertCustomField.SELECT and field.options:
                choices = [(option, option) for option in field.options]
                self.fields[field_name] = forms.ChoiceField(choices=choices, **field_kwargs)
    
    def save(self, alert):
        """Save the custom field values for an alert"""
        if not self.organization:
            return
        
        custom_fields = AlertCustomField.objects.filter(organization=self.organization)
        
        # Process each custom field
        for field in custom_fields:
            field_name = f"custom_{field.name}"
            if field_name in self.cleaned_data:
                value = self.cleaned_data[field_name]
                
                # Convert to string representation
                if value is None:
                    value = ''
                elif isinstance(value, bool):
                    value = '1' if value else '0'
                else:
                    value = str(value)
                
                # Create or update the custom value
                AlertCustomValue.objects.update_or_create(
                    alert=alert,
                    field=field,
                    defaults={'value': value}
                ) 