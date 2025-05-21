from django import forms
from django.utils.translation import gettext_lazy as _

from .models import MISPInstance, ThreatIntelligenceItem


class MISPInstanceForm(forms.ModelForm):
    """Formulário para criar e editar instâncias MISP"""
    
    class Meta:
        model = MISPInstance
        fields = [
            'name', 'description', 'url', 'api_key', 'verify_ssl',
            'import_events', 'import_attributes', 'import_tags', 'import_galaxies', 'import_from_days',
            'tags_to_include', 'tags_to_exclude', 'is_public', 'sync_frequency'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'api_key': forms.PasswordInput(render_value=True),
            'tags_to_include': forms.Textarea(attrs={'rows': 2, 'placeholder': 'tag1, tag2, tag3'}),
            'tags_to_exclude': forms.Textarea(attrs={'rows': 2, 'placeholder': 'tag1, tag2, tag3'}),
        }
        help_texts = {
            'sync_frequency': _('How often to sync with this MISP instance (in minutes)'),
            'api_key': _('API key from your MISP instance. This will be stored encrypted.'),
            'import_from_days': _('Import events from the last X days. Use 0 for all events.'),
            'import_tags': _('Import all tag definitions from the MISP instance.'),
            'import_galaxies': _('Import all galaxies and clusters from the MISP instance.'),
        }


class ThreatIntelligenceSearchForm(forms.Form):
    """Formulário para busca de indicadores de ameaças"""
    
    ITEM_TYPE_CHOICES = [('', '---')] + list(ThreatIntelligenceItem.TYPE_CHOICES)
    CONFIDENCE_CHOICES = [('', '---'), ('low', _('Low')), ('medium', _('Medium')), ('high', _('High'))]
    TLP_CHOICES = [
        ('', '---'),
        ('white', 'TLP:WHITE'),
        ('green', 'TLP:GREEN'),
        ('amber', 'TLP:AMBER'),
        ('red', 'TLP:RED'),
    ]
    
    search_term = forms.CharField(
        label=_('Search Term'),
        required=False,
        widget=forms.TextInput(attrs={'placeholder': _('IP, domain, hash, etc.')})
    )
    
    item_type = forms.ChoiceField(
        label=_('Type'),
        choices=ITEM_TYPE_CHOICES,
        required=False,
    )
    
    confidence = forms.ChoiceField(
        label=_('Confidence'),
        choices=CONFIDENCE_CHOICES,
        required=False,
    )
    
    is_malicious = forms.NullBooleanField(
        label=_('Malicious'),
        required=False,
        widget=forms.Select(choices=[
            ('', '---'),
            ('true', _('Yes')),
            ('false', _('No')),
        ])
    )
    
    tlp = forms.ChoiceField(
        label=_('TLP'),
        choices=TLP_CHOICES,
        required=False,
    )
    
    creator_org = forms.CharField(
        label=_('Creator Organization'),
        required=False,
        widget=forms.TextInput(attrs={'placeholder': _('Filter by organization')})
    ) 