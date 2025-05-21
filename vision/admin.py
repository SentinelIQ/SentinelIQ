from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (
    ThreatIntelligenceFeed, MISPInstance, ThreatIntelligenceItem,
    MISPTag, MISPGalaxy, MISPCluster
)


@admin.register(ThreatIntelligenceFeed)
class ThreatIntelligenceFeedAdmin(admin.ModelAdmin):
    list_display = ('name', 'feed_type', 'status', 'organization', 'is_public', 'last_sync')
    list_filter = ('feed_type', 'status', 'organization', 'is_public')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at', 'last_sync')
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'feed_type', 'organization', 'is_public')
        }),
        (_('Status'), {
            'fields': ('status', 'last_sync')
        }),
        (_('Synchronization'), {
            'fields': ('sync_frequency',)
        }),
        (_('Audit'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(MISPInstance)
class MISPInstanceAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'organization', 'status', 'last_sync')
    list_filter = ('status', 'organization', 'verify_ssl', 'import_events', 'import_attributes', 'import_tags', 'import_galaxies')
    search_fields = ('name', 'url', 'description')
    readonly_fields = ('created_at', 'updated_at', 'last_sync')
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'organization', 'is_public')
        }),
        (_('Connection'), {
            'fields': ('url', 'api_key', 'verify_ssl')
        }),
        (_('Import Settings'), {
            'fields': ('import_events', 'import_attributes', 'import_tags', 'import_galaxies', 'import_from_days', 'tags_to_include', 'tags_to_exclude')
        }),
        (_('Status'), {
            'fields': ('status', 'last_sync', 'sync_frequency')
        }),
        (_('Audit'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ThreatIntelligenceItem)
class ThreatIntelligenceItemAdmin(admin.ModelAdmin):
    list_display = ('item_type', 'value_short', 'feed', 'creator_org', 'attribute_count', 'correlation_count', 'is_malicious', 'tlp', 'last_seen')
    list_filter = ('item_type', 'is_malicious', 'confidence', 'tlp', 'feed', 'creator_org', 'owner_org')
    search_fields = ('value', 'description', 'tags', 'external_id', 'creator_org', 'creator_user')
    readonly_fields = ('created_at', 'updated_at', 'first_seen', 'last_seen', 'attribute_count', 'correlation_count')
    
    def value_short(self, obj):
        return obj.value[:50] + ('...' if len(obj.value) > 50 else '')
    
    value_short.short_description = _('Value')
    
    fieldsets = (
        (None, {
            'fields': ('feed', 'item_type', 'value', 'description', 'tags')
        }),
        (_('MISP Event Information'), {
            'fields': ('creator_org', 'owner_org', 'creator_user', 'event_date', 'distribution', 
                      'attribute_count', 'correlation_count')
        }),
        (_('Classification'), {
            'fields': ('is_malicious', 'confidence', 'tlp')
        }),
        (_('External Information'), {
            'fields': ('external_id', 'external_url')
        }),
        (_('Timestamps'), {
            'fields': ('first_seen', 'last_seen', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(MISPTag)
class MISPTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'feed', 'colour', 'is_system', 'is_hidden')
    list_filter = ('feed', 'is_system', 'is_hidden')
    search_fields = ('name', 'external_id')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(MISPGalaxy)
class MISPGalaxyAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'feed', 'version')
    list_filter = ('feed', 'type')
    search_fields = ('name', 'description', 'type')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(MISPCluster)
class MISPClusterAdmin(admin.ModelAdmin):
    list_display = ('value', 'galaxy', 'source')
    list_filter = ('galaxy', 'source')
    search_fields = ('value', 'description', 'uuid')
    readonly_fields = ('created_at', 'updated_at') 