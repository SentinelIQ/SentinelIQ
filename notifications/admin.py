from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import NotificationDestination, NotificationRule, NotificationLog, NotificationEvent


@admin.register(NotificationDestination)
class NotificationDestinationAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'organization', 'is_active', 'created_at')
    list_filter = ('type', 'organization', 'is_active')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'type', 'organization', 'is_active')
        }),
        (_('Configuration'), {
            'fields': ('config',),
            'description': _('Configuration depends on the destination type. For email, include recipients. For webhooks, include URL and headers.')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(NotificationRule)
class NotificationRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'source', 'event_type', 'organization', 'is_active')
    list_filter = ('source', 'event_type', 'organization', 'is_active')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('destinations',)
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'organization', 'is_active')
        }),
        (_('Event Configuration'), {
            'fields': ('source', 'event_type', 'conditions')
        }),
        (_('Destinations'), {
            'fields': ('destinations',)
        }),
        (_('Templates'), {
            'fields': ('template_subject', 'template_body'),
            'description': _('Templates support variables in {{variable}} format. Available variables depend on the event source.')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('rule', 'destination', 'status', 'created_at', 'sent_at', 'organization')
    list_filter = ('status', 'organization', 'created_at')
    search_fields = ('subject', 'body', 'error_message')
    readonly_fields = ('rule', 'destination', 'event_data', 'status', 'subject', 'body', 
                      'error_message', 'created_at', 'sent_at', 'organization', 'tracking_id')
    fieldsets = (
        (None, {
            'fields': ('rule', 'destination', 'organization', 'tracking_id')
        }),
        (_('Status'), {
            'fields': ('status', 'created_at', 'sent_at')
        }),
        (_('Content'), {
            'fields': ('subject', 'body')
        }),
        (_('Event Data'), {
            'fields': ('event_data',),
            'classes': ('collapse',)
        }),
        (_('Error'), {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(NotificationEvent)
class NotificationEventAdmin(admin.ModelAdmin):
    list_display = ('source_type', 'event_type', 'source_id', 'processed', 'created_at', 'organization')
    list_filter = ('source_type', 'event_type', 'processed', 'organization')
    search_fields = ('source_id',)
    readonly_fields = ('source_type', 'event_type', 'source_id', 'event_data', 'processed', 'created_at', 'organization')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
