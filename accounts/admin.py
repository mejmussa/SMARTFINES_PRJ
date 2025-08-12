from django.contrib import admin
from django.utils.html import format_html
from .models import GuestVisit, User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    model = User
    list_display = ['email', 'username', 'phone', 'carrier_name', 'Image', 'slug', 'created_at', 'is_active', 'is_superuser', 'is_staff']
    list_filter = ['is_active', 'username', 'is_superuser', 'is_staff']
    search_fields = ['email', 'username']
    ordering = ['email', 'username', 'phone']


@admin.register(GuestVisit)
class GuestVisitAdmin(admin.ModelAdmin):
    # Display the following fields in the list view
    list_display = [
        'timestamp', 'ip_address', 'platform', 'browser', 'browser_version', 'timezone']



