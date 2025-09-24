from django.db import models
from accounts.models import User
from datetime import timedelta
import africastalking
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver


# Initialize Africa's Talking SDK
africastalking.initialize(
    username=settings.AT_USERNAME,  # e.g., "sandbox" or your live username
    api_key=settings.AT_API_KEY     # your Africa's Talking API key
)

sms = africastalking.SMS



class Vehicle(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="vehicles")
    plate_number = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    check_interval = models.PositiveIntegerField(default=43200)  # seconds, default 12 hours
    last_checked = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.plate_number} ({self.user.username})"

class TrafficOffense(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="offenses")
    reference = models.CharField(max_length=50)
    license = models.CharField(max_length=50)
    location = models.CharField(max_length=100)
    offence = models.TextField()
    charge = models.DecimalField(max_digits=10, decimal_places=2)
    penalty = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20)
    issued_date = models.DateTimeField()
    is_paid = models.BooleanField(default=False)
    sms_sent = models.BooleanField(default=False)

    class Meta:
        unique_together = ['vehicle', 'reference']

    def __str__(self):
        return f"{self.vehicle.plate_number} - {self.reference}"
    

@receiver(post_save, sender=TrafficOffense)
def send_offense_alert(sender, instance, created, **kwargs):
    if created and not instance.sms_sent:
        vehicle = instance.vehicle
        user = vehicle.user
        if not user.phone:
            print(f"No phone number for user {user.username}")
            return

        total_offenses = vehicle.offenses.count()  # Count all offenses for the vehicle
        message = f"""SmartFines Alert
Your vehicle {vehicle.plate_number} has {total_offenses} offense(s).
Please check your account for details.
"""
        try:
            response = sms.send(
                message=message,
                recipients=[str(user.phone)],
                sender_id="SmartFines"
            )
            # Mark all unsent offenses for this vehicle as sent to avoid duplicate SMS
            vehicle.offenses.filter(sms_sent=False).update(sms_sent=True)
            print(f"SMS sent to {user.phone} for vehicle {vehicle.plate_number}")
        except Exception as e:
            print(f"Error sending SMS: {e}")


class Balance(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="balance")
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - TZS {self.amount}"

class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('DEPOSIT', 'Deposit'),
        ('PAYMENT', 'Payment'),
        ('PENALTY', 'Penalty'),
        ('WITHDRAWAL', 'Withdrawal'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transactions")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    related_offense = models.ForeignKey(TrafficOffense, on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions")

    def __str__(self):
        return f"{self.user.username} - {self.transaction_type} - TZS {self.amount}"
    



class CheckerConfig(models.Model):
    is_enabled = models.BooleanField(
        default=False,
        help_text="Enable or disable the traffic offense checker. Only admin users can modify this."
    )

    class Meta:
        verbose_name = "Checker Configuration"
        verbose_name_plural = "Checker Configurations"

    def __str__(self):
        return f"Checker Enabled: {self.is_enabled}"
