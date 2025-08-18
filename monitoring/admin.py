from django.contrib import admin
from .models import TrafficOffense, Vehicle

@admin.register(TrafficOffense)
class TrafficOffenseAdmin(admin.ModelAdmin):
    list_display = [
        "vehicle", "reference", "license", "location", "offence", 
        "charge", "penalty", "status", "is_paid", "formatted_issued_date"
    ]
    search_fields = ["reference", "offence"]

    def formatted_issued_date(self, obj):
        # Format the date as: 2025-06-05 14:23:49
        return obj.issued_date.strftime("%Y-%m-%d %H:%M:%S")

    formatted_issued_date.admin_order_field = 'issued_date'
    formatted_issued_date.short_description = 'Issued Date'

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ["plate_number", "user", "make", "model", "year", "created_at"]
    search_fields = ["plate_number", "make", "model", "user__username"]
    list_filter = ["make", "year", "user"]
