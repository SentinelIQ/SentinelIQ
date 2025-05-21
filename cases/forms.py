from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Case, CaseComment, CaseAttachment, CaseEvent


class CaseForm(forms.ModelForm):
    """Form for creating and updating cases"""
    
    class Meta:
        model = Case
        fields = (
            'title', 'description', 'priority', 'status', 
            'assigned_to', 'due_date', 'related_alerts', 'tlp', 'pap', 'tags'
        )
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'related_alerts': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'tlp': forms.Select(attrs={'class': 'form-select'}),
            'pap': forms.Select(attrs={'class': 'form-select'}),
            'tags': forms.SelectMultiple(attrs={'class': 'form-select', 'size': '5'}),
        }
    
    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields['assigned_to'].queryset = organization.users.all()
            self.fields['related_alerts'].queryset = organization.alerts.all()


class CaseCommentForm(forms.ModelForm):
    """Form for adding comments to cases"""
    
    class Meta:
        model = CaseComment
        fields = ('content',)
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': _('Add a comment...')}),
        }


class CaseAttachmentForm(forms.ModelForm):
    """Form for uploading attachments to cases"""
    
    class Meta:
        model = CaseAttachment
        fields = ('file',)
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.filename = self.cleaned_data['file'].name
        if commit:
            instance.save()
        return instance


class CaseFilterForm(forms.Form):
    """Form for filtering cases"""
    STATUS_CHOICES = [('', _('All Statuses'))] + list(Case.STATUS_CHOICES)
    PRIORITY_CHOICES = [('', _('All Priorities'))] + list(Case.PRIORITY_CHOICES)
    TLP_CHOICES = [('', _('All TLP'))] + list(Case.TLP_CHOICES)
    PAP_CHOICES = [('', _('All PAP'))] + list(Case.PAP_CHOICES)
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES, 
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    priority = forms.ChoiceField(
        choices=PRIORITY_CHOICES, 
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
    assigned_to = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label=_('All Assignees'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Search by title or description')
        })
    )
    
    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields['assigned_to'].queryset = organization.users.all()
        else:
            from accounts.models import User
            self.fields['assigned_to'].queryset = User.objects.none()

        from core.models import Tag
        self.fields['tag'].queryset = Tag.objects.all()


class CaseEventForm(forms.ModelForm):
    """Form for adding custom events to case timeline"""
    
    class Meta:
        model = CaseEvent
        fields = ('title', 'description')
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Event title'),
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 2, 
                'placeholder': _('Event description (optional)'),
            }),
        }
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.event_type = CaseEvent.CUSTOM
        if commit:
            instance.save()
        return instance 