from django.conf import settings
from django.db import models
from django.utils import timezone

SLOT_TYPES = ["Car", "Bike", "EV", "Accessible"]
SLOT_STATUSES = ["available", "occupied", "maintenance"]


class Slot(models.Model):
    label = models.CharField(max_length=10, unique=True)
    zone = models.CharField(max_length=10)
    slot_type = models.CharField(max_length=12, default="Car")
    status = models.CharField(max_length=12, default="available")

    class Meta:
        ordering = ["zone", "label"]

    def __str__(self):
        return f"{self.label} ({self.status})"


class Booking(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookings")
    slot = models.ForeignKey(Slot, on_delete=models.CASCADE, related_name="bookings")
    name = models.CharField(max_length=60)
    vehicle_number = models.CharField(max_length=15)
    status = models.CharField(max_length=12, default="active")
    created_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-id"]

    # Convenience names used by the templates (same names as the Flask version).
    @property
    def slot_label(self):
        return self.slot.label

    @property
    def slot_zone(self):
        return self.slot.zone

    @property
    def slot_type(self):
        return self.slot.slot_type

    @property
    def account(self):
        return self.user.username

    def __str__(self):
        return f"KB-{self.id} {self.vehicle_number} ({self.status})"
