from django.contrib import admin
from .models import TrafficOffense, Vehicle, Balance, Transaction
from accounts.models import User

@admin.register(TrafficOffense)
class TrafficOffenseAdmin(admin.ModelAdmin):
    list_display = [
        "vehicle", "reference", "license", "location", "offence", 
        "charge", "penalty", "status", "is_paid", "sms_sent", "formatted_issued_date"
    ]
    search_fields = ["reference", "offence"]

    def formatted_issued_date(self, obj):
        # Format the date as: 2025-06-05 14:23:49
        return obj.issued_date.strftime("%Y-%m-%d %H:%M:%S")

    formatted_issued_date.admin_order_field = 'issued_date'
    formatted_issued_date.short_description = 'Issued Date'

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ["plate_number", "user", "created_at"]
    search_fields = ["plate_number", "user__username"]
    list_filter = ["user"]

@admin.register(Balance)
class BalanceAdmin(admin.ModelAdmin):
    list_display = ["user", "amount", "updated_at"]
    search_fields = ["user__username"]
    list_filter = ["updated_at"]
    readonly_fields = ["updated_at"]

    def get_queryset(self, request):
        # Optimize query by selecting related user
        return super().get_queryset(request).select_related("user")

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["user", "transaction_type", "amount", "description", "related_offense", "created_at"]
    search_fields = ["user__username", "transaction_type", "description"]
    list_filter = ["transaction_type", "created_at"]
    readonly_fields = ["created_at"]

    def get_queryset(self, request):
        # Optimize query by selecting related user and offense
        return super().get_queryset(request).select_related("user", "related_offense")