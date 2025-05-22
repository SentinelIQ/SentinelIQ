from django import forms
from django.utils.translation import gettext_lazy as _
from .models import NotificationDestination, NotificationRule
import json


class NotificationDestinationForm(forms.ModelForm):
    """Form for managing notification destinations"""
    
    # JSON config field represented as a text area
    config_json = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        label=_('Configuration (JSON)'),
        required=False,
        help_text=_('JSON configuration for the destination')
    )
    
    class Meta:
        model = NotificationDestination
        fields = ('name', 'type', 'is_active')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
    
    def __init__(self, *args, **kwargs):
        self.organization = kwargs.pop('organization', None)
        instance = kwargs.get('instance')
        
        super().__init__(*args, **kwargs)
        
        # If we have an instance, convert its JSON config to a string for the text area
        if instance and instance.config:
            self.fields['config_json'].initial = json.dumps(instance.config, indent=2)
    
    def clean_config_json(self):
        """Validate and convert JSON string to Python dict"""
        config_json = self.cleaned_data.get('config_json', '')
        
        if not config_json:
            return {}
        
        try:
            config = json.loads(config_json)
            
            # Validate configuration based on destination type
            dest_type = self.cleaned_data.get('type')
            
            if dest_type == NotificationDestination.EMAIL:
                if 'recipients' not in config or not config['recipients']:
                    raise forms.ValidationError(_('Email configuration must include "recipients" list.'))
                
                # Validate recipients is a list
                if not isinstance(config['recipients'], list):
                    raise forms.ValidationError(_('Recipients must be a list of email addresses.'))
            
            elif dest_type in (NotificationDestination.WEBHOOK, NotificationDestination.CUSTOM_HTTP):
                if 'url' not in config or not config['url']:
                    raise forms.ValidationError(_('Webhook/HTTP configuration must include "url" field.'))
            
            elif dest_type in (NotificationDestination.SLACK, NotificationDestination.MATTERMOST):
                if 'webhook_url' not in config or not config['webhook_url']:
                    raise forms.ValidationError(_('Slack/Mattermost configuration must include "webhook_url" field.'))
            
            return config
            
        except json.JSONDecodeError:
            raise forms.ValidationError(_('Invalid JSON configuration.'))
    
    def clean(self):
        """Validate the form"""
        cleaned_data = super().clean()
        
        # Add the config_json as config in the cleaned data
        if 'config_json' in cleaned_data:
            cleaned_data['config'] = cleaned_data.pop('config_json')
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save the model with the organization"""
        instance = super().save(commit=False)
        
        # Set the organization if provided
        if self.organization:
            instance.organization = self.organization
        
        if commit:
            instance.save()
        
        return instance


class NotificationRuleForm(forms.ModelForm):
    """Form for managing notification rules"""
    
    # JSON conditions field represented as a text area
    conditions_json = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label=_('Conditions (JSON)'),
        required=False,
        help_text=_('JSON conditions that must be met to trigger notification')
    )
    
    class Meta:
        model = NotificationRule
        fields = (
            'name', 'description', 'source', 'event_type',
            'template_subject', 'template_body', 'destinations',
            'is_active'
        )
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'source': forms.Select(attrs={'class': 'form-select'}),
            'event_type': forms.Select(attrs={'class': 'form-select'}),
            'template_subject': forms.TextInput(attrs={'class': 'form-control'}),
            'template_body': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'destinations': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
    
    def __init__(self, *args, **kwargs):
        self.organization = kwargs.pop('organization', None)
        instance = kwargs.get('instance')
        
        super().__init__(*args, **kwargs)
        
        # If we have an instance, convert its JSON conditions to a string for the text area
        if instance and instance.conditions:
            self.fields['conditions_json'].initial = json.dumps(instance.conditions, indent=2)
        
        # Filter destinations by organization
        if self.organization:
            self.fields['destinations'].queryset = NotificationDestination.objects.filter(
                organization=self.organization,
                is_active=True
            )
    
    def clean_conditions_json(self):
        """Validate and convert JSON string to Python dict"""
        conditions_json = self.cleaned_data.get('conditions_json', '')
        
        if not conditions_json:
            return {}
        
        try:
            conditions = json.loads(conditions_json)
            
            # Basic validation that conditions is a dictionary
            if not isinstance(conditions, dict):
                raise forms.ValidationError(_('Conditions must be a JSON object (dictionary).'))
            
            return conditions
            
        except json.JSONDecodeError:
            raise forms.ValidationError(_('Invalid JSON conditions.'))
    
    def clean(self):
        """Validate the form"""
        cleaned_data = super().clean()
        
        # Add the conditions_json as conditions in the cleaned data
        if 'conditions_json' in cleaned_data:
            cleaned_data['conditions'] = cleaned_data.pop('conditions_json')
        
        # Validate that there is at least one destination
        if 'destinations' not in cleaned_data or not cleaned_data['destinations']:
            self.add_error('destinations', _('At least one destination is required.'))
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save the model with the organization"""
        instance = super().save(commit=False)
        
        # Set the organization if provided
        if self.organization:
            instance.organization = self.organization
        
        if commit:
            instance.save()
            
            # Save many-to-many fields
            self.save_m2m()
        
        return instance 