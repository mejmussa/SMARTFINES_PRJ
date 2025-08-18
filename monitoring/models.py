from django.db import models
from accounts.models import User



class TrafficOffense(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plate_number = models.CharField(max_length=20)
    reference = models.CharField(max_length=50)
    license = models.CharField(max_length=50)
    location = models.CharField(max_length=100)
    offence = models.TextField()
    charge = models.DecimalField(max_digits=10, decimal_places=2)
    penalty = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20)
    issued_date = models.DateTimeField()
    is_paid = models.BooleanField(default=False)  # New field

    class Meta:
        unique_together = ['plate_number', 'reference']

    def __str__(self):
        return f"{self.plate_number} - {self.reference}"



