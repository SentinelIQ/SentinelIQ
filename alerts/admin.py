from django.contrib import admin
from .models import Alert

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('title', 'organization', 'severity', 'status', 'assigned_to', 'created_at')
    list_filter = ('severity', 'status', 'organization')
    search_fields = ('title', 'description')
    raw_id_fields = ('assigned_to',)
