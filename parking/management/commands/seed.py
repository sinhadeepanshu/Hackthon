from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from parking.models import Booking, Slot


class Command(BaseCommand):
    help = "Create the demo admin, a demo driver and sample parking slots (safe to run more than once)."

    def handle(self, *args, **options):
        User = get_user_model()
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@kerbside.local", "Admin@123", first_name="Parking Admin")
            self.stdout.write("Created staff user: admin / Admin@123")
        demo = User.objects.filter(username="demo").first()
        if not demo:
            demo = User.objects.create_user("demo", "demo@kerbside.local", "Demo@123", first_name="Demo Driver")
            self.stdout.write("Created driver user: demo / Demo@123")
        if not Slot.objects.exists():
            counters = {}
            for zone, kind, count in [("A", "Car", 8), ("B", "Car", 6), ("B", "Accessible", 2), ("C", "Bike", 6), ("D", "EV", 4)]:
                for _ in range(count):
                    counters[zone] = counters.get(zone, 0) + 1
                    Slot.objects.create(label=f"{zone}{counters[zone]}", zone=zone, slot_type=kind)
            a3 = Slot.objects.get(label="A3")
            Booking.objects.create(user=demo, slot=a3, name="Demo Driver", vehicle_number="KA01AB1234")
            Slot.objects.filter(label__in=["A3", "A6", "B2"]).update(status="occupied")
            Slot.objects.filter(label="C4").update(status="maintenance")
            self.stdout.write("Created sample parking slots.")
        self.stdout.write(self.style.SUCCESS("Seed complete."))
