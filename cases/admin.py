from django.contrib import admin
from .models import Case, CaseComment, CaseAttachment, CaseEvent

class CaseCommentInline(admin.TabularInline):
    model = CaseComment
    extra = 0

class CaseAttachmentInline(admin.TabularInline):
    model = CaseAttachment
    extra = 0

class CaseEventInline(admin.TabularInline):
    model = CaseEvent
    extra = 0
    readonly_fields = ('created_at',)

@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ('title', 'organization', 'status', 'priority', 'assigned_to', 'created_at')
    list_filter = ('status', 'priority', 'organization')
    search_fields = ('title', 'description')
    date_hierarchy = 'created_at'
    inlines = [CaseCommentInline, CaseAttachmentInline, CaseEventInline]

@admin.register(CaseEvent)
class CaseEventAdmin(admin.ModelAdmin):
    list_display = ('case', 'event_type', 'title', 'user', 'created_at')
    list_filter = ('event_type', 'case__organization')
    search_fields = ('title', 'description', 'case__title')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)
