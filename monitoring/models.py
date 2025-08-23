from django.db import models
from accounts.models import User

class Vehicle(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="vehicles")
    plate_number = models.CharField(max_length=20, unique=True)
    make = models.CharField(max_length=50, blank=True, null=True)
    model = models.CharField(max_length=50, blank=True, null=True)
    year = models.PositiveSmallIntegerField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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

    class Meta:
        unique_together = ['vehicle', 'reference']

    def __str__(self):
        return f"{self.vehicle.plate_number} - {self.reference}"

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