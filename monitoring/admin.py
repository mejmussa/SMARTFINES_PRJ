from django.contrib import admin
from .models import TrafficOffense

@admin.register(TrafficOffense)
class TrafficOffenseAdmin(admin.ModelAdmin):
    list_display = ["user", "plate_number", "reference", "license", "location", "offence", "charge", "status", "is_paid", "is_paid", "formatted_issued_date"]
    search_fields = ["plate_number", "reference", "offence"]

    def formatted_issued_date(self, obj):
        # Format the date as: 2025-06-05 14:23:49
        return obj.issued_date.strftime("%Y-%m-%d %H:%M:%S")

    # This is optional but helps sorting by issued_date in admin list
    formatted_issued_date.admin_order_field = 'issued_date'
    formatted_issued_date.short_description = 'Issued Date'
