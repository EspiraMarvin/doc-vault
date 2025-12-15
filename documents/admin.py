from django.contrib import admin

# Register your models here.
from .models import Document, DocumentVersion, Tag, AuditLog, SharedDocument


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "owner", "created_at", "updated_at")
    # search_fields = ('title', 'description', 'owner__username')
    # list_filter = ('created_at', 'updated_at')


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ("id", "document", "version_number", "uploaded_by", "created_at")
    # search_fields = ('document__title', 'uploaded_by__username')
    # list_filter = ('created_at',)


# admin.site.register(Document)
# admin.site.register(DocumentVersion)
admin.site.register(Tag)
admin.site.register(AuditLog)
admin.site.register(SharedDocument)
