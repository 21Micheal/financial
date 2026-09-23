"""
audit/admin.py
"""
from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'event', 'actor', 'object_repr']
    list_filter = ['event']
    search_fields = ['actor__email', 'object_repr']
    readonly_fields = ['id', 'timestamp']
