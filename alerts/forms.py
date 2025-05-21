from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Alert


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