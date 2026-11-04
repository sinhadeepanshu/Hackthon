import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Slot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(max_length=10, unique=True)),
                ("zone", models.CharField(max_length=10)),
                ("slot_type", models.CharField(default="Car", max_length=12)),
                ("status", models.CharField(default="available", max_length=12)),
            ],
            options={"ordering": ["zone", "label"]},
        ),
        migrations.CreateModel(
            name="Booking",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=60)),
                ("vehicle_number", models.CharField(max_length=15)),
                ("status", models.CharField(default="active", max_length=12)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                ("slot", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="bookings", to="parking.slot")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="bookings", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-id"]},
        ),
    ]
