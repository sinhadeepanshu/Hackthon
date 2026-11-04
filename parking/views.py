"""Kerbside Smart Parking Management System - Django views."""
import re
from functools import wraps

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .models import SLOT_STATUSES, SLOT_TYPES, Booking, Slot

User = get_user_model()


# ------------------------------------------------------------ access control
def driver_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('login')}?next={request.path}")
        if request.user.is_staff:
            messages.info(request, "Staff accounts manage parking. Sign in with a driver account to book a slot.")
            return redirect("admin_dashboard")
        return view(request, *args, **kwargs)
    return wrapper


def admin_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("admin_login")
        if not request.user.is_staff:
            messages.error(request, "You do not have access to that page.")
            return redirect("home")
        return view(request, *args, **kwargs)
    return wrapper


def login_required_any(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('login')}?next={request.path}")
        return view(request, *args, **kwargs)
    return wrapper


# ------------------------------------------------------------ helpers
def sort_slots(slots):
    return sorted(slots, key=lambda s: (s.zone, len(s.label), s.label))


def snapshot():
    slots = sort_slots(Slot.objects.all())
    zones = {}
    for s in slots:
        zones.setdefault(s.zone, []).append(s)
    counts = {"total": len(slots)}
    for status in SLOT_STATUSES:
        counts[status] = sum(1 for s in slots if s.status == status)
    return [{"name": n, "slots": v} for n, v in zones.items()], counts, slots


def normalise_vehicle(value):
    # Spaces and hyphens are ignored so "KA 01 AB 1234" and "KA01AB1234" are the same vehicle.
    return re.sub(r"[\s\-]+", "", value.upper())


def validate_booking(name, vehicle):
    errors = []
    if not 2 <= len(name) <= 60:
        errors.append("Enter your name (2 to 60 characters).")
    if not re.fullmatch(r"[A-Z0-9]{4,15}", vehicle):
        errors.append("Enter a valid vehicle registration number, for example KA01AB1234.")
    return errors


def validate_slot(data, slot_id=None):
    errors = []
    label = data.get("label", "").strip().upper()
    zone = data.get("zone", "").strip().upper()
    slot_type, status = data.get("slot_type"), data.get("status")
    if not re.fullmatch(r"[A-Z0-9\-]{1,10}", label):
        errors.append("Slot label must be 1 to 10 letters, numbers or hyphens.")
    if not re.fullmatch(r"[A-Z0-9 ]{1,10}", zone):
        errors.append("Zone must be 1 to 10 letters or numbers.")
    if slot_type not in SLOT_TYPES:
        errors.append("Choose a valid slot type.")
    if status not in SLOT_STATUSES:
        errors.append("Choose a valid status.")
    if Slot.objects.filter(label=label).exclude(pk=slot_id or 0).exists():
        errors.append(f"A slot labelled {label} already exists.")
    return errors, {"label": label, "zone": zone, "slot_type": slot_type, "status": status}


def safe_next(request):
    target = request.POST.get("next") or request.GET.get("next") or ""
    ok = url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}) if target else False
    return target if ok else ""


# ------------------------------------------------------------ public + driver views
def home(request):
    zones, counts, _ = snapshot()
    return render(request, "home.html", {"zones": zones, "counts": counts, "page": "home"})


def slots(request):
    zones, counts, _ = snapshot()
    return render(request, "slots.html", {"zones": zones, "counts": counts, "page": "slots"})


def api_slots(request):
    _, counts, all_slots = snapshot()
    return JsonResponse({"slots": [{"id": s.id, "label": s.label, "status": s.status} for s in all_slots], "counts": counts})


def register(request):
    if request.user.is_authenticated:
        return redirect("slots")
    form = {"full_name": "", "username": "", "email": ""}
    errors = []
    if request.method == "POST":
        form = {k: request.POST.get(k, "").strip() for k in form}
        password, confirm = request.POST.get("password", ""), request.POST.get("confirm", "")
        if not 2 <= len(form["full_name"]) <= 60:
            errors.append("Enter your full name.")
        if not re.fullmatch(r"\w{3,30}", form["username"]):
            errors.append("Username must be 3 to 30 letters, numbers or underscores.")
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", form["email"]):
            errors.append("Enter a valid email address.")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if password != confirm:
            errors.append("The two passwords do not match.")
        if not errors and User.objects.filter(username__iexact=form["username"]).exists():
            errors.append("That username is taken. Try another one.")
        if not errors:
            user = User.objects.create_user(username=form["username"], email=form["email"], password=password,
                                            first_name=form["full_name"])
            login(request, user)
            messages.success(request, "Account created. You can book a slot now.")
            return redirect("slots")
    return render(request, "register.html", {"form": form, "errors": errors, "page": "register"})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("admin_dashboard" if request.user.is_staff else "slots")
    errors, username = [], ""
    next_url = safe_next(request)
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        user = authenticate(request, username=username, password=request.POST.get("password", ""))
        if user is None:
            errors.append("Incorrect username or password.")
        elif user.is_staff:
            errors.append("This is a staff account. Please use the staff portal to sign in.")
        else:
            login(request, user)
            return redirect(next_url or "slots")
    return render(request, "login.html", {"errors": errors, "username": username, "next": next_url, "page": "login"})


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, "You have been signed out.")
    return redirect("home")


@driver_required
def book(request, slot_id):
    slot = get_object_or_404(Slot, pk=slot_id)
    if slot.status != "available":
        messages.error(request, f"Slot {slot.label} is no longer available. Please choose another one.")
        return redirect("slots")
    form, errors = {"name": request.user.first_name, "vehicle_number": ""}, []
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        vehicle = normalise_vehicle(request.POST.get("vehicle_number", ""))
        form = {"name": name, "vehicle_number": vehicle}
        errors = validate_booking(name, vehicle)
        if not errors:
            booking = None
            with transaction.atomic():
                # Atomic claim: only succeeds if the slot is still available (prevents double booking).
                claimed = Slot.objects.filter(pk=slot_id, status="available").update(status="occupied")
                if not claimed:
                    messages.error(request, f"Sorry, slot {slot.label} was just taken. Please choose another one.")
                    return redirect("slots")
                if Booking.objects.filter(vehicle_number=vehicle, status="active").exists():
                    transaction.set_rollback(True)
                    errors.append(f"Vehicle {vehicle} already has an active booking.")
                else:
                    booking = Booking.objects.create(user=request.user, slot=slot, name=name, vehicle_number=vehicle)
            if booking:
                messages.success(request, f"Slot {slot.label} booked successfully.")
                return redirect(reverse("booking_detail", args=[booking.id]) + "?new=1")
    return render(request, "book.html", {"slot": slot, "form": form, "errors": errors, "page": "slots"})


@login_required_any
def booking_detail(request, booking_id):
    booking = get_object_or_404(Booking.objects.select_related("slot", "user"), pk=booking_id)
    if not request.user.is_staff and booking.user_id != request.user.id:
        return render(request, "404.html", status=404)
    return render(request, "booking_detail.html", {
        "booking": booking, "just_booked": request.GET.get("new") == "1",
        "can_cancel": booking.user_id == request.user.id, "page": "my_bookings"})


@driver_required
def my_bookings(request):
    rows = Booking.objects.filter(user=request.user).select_related("slot", "user")
    return render(request, "my_bookings.html", {"bookings": rows, "page": "my_bookings"})


@driver_required
@require_POST
def cancel(request, booking_id):
    booking = get_object_or_404(Booking.objects.select_related("slot"), pk=booking_id, user=request.user)
    with transaction.atomic():
        changed = Booking.objects.filter(pk=booking_id, status="active").update(status="cancelled", ended_at=timezone.now())
        if changed:
            Slot.objects.filter(pk=booking.slot_id, status="occupied").update(status="available")
    if changed:
        messages.success(request, f"Booking KB-{booking_id} cancelled. Slot {booking.slot.label} is free again.")
    else:
        messages.error(request, "That booking is not active.")
    return redirect("my_bookings")


# ------------------------------------------------------------ staff views
def admin_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("admin_dashboard")
    errors, username = [], ""
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        user = authenticate(request, username=username, password=request.POST.get("password", ""))
        if user is not None and user.is_staff:
            login(request, user)
            return redirect("admin_dashboard")
        errors.append("Incorrect admin username or password.")
    return render(request, "admin_login.html", {"errors": errors, "username": username, "page": "admin_login"})


@admin_required
def admin_dashboard(request):
    _, counts, _ = snapshot()
    stats = {"active_bookings": Booking.objects.filter(status="active").count(),
             "drivers": User.objects.filter(is_staff=False).count()}
    recent = Booking.objects.select_related("slot", "user")[:6]
    return render(request, "admin_dashboard.html", {"counts": counts, "stats": stats, "recent": recent, "page": "dashboard"})


def _render_admin_slots(request, form, errors):
    active = {b.slot_id: b.vehicle_number for b in Booking.objects.filter(status="active")}
    rows = sort_slots(Slot.objects.all())
    for s in rows:
        s.vehicle_number = active.get(s.id)
    return render(request, "admin_slots.html", {"slots": rows, "form": form, "errors": errors, "types": SLOT_TYPES,
                                               "statuses": SLOT_STATUSES, "page": "admin_slots"})


@admin_required
def admin_slots(request):
    return _render_admin_slots(request, {"label": "", "zone": "", "slot_type": "Car", "status": "available"}, [])


@admin_required
@require_POST
def admin_slot_add(request):
    errors, clean = validate_slot(request.POST)
    if errors:
        return _render_admin_slots(request, request.POST, errors)
    Slot.objects.create(**clean)
    messages.success(request, f"Slot {clean['label']} added.")
    return redirect("admin_slots")


@admin_required
def admin_slot_edit(request, slot_id):
    slot = get_object_or_404(Slot, pk=slot_id)
    form, errors = slot, []
    if request.method == "POST":
        errors, clean = validate_slot(request.POST, slot_id)
        form = request.POST
        if not errors:
            with transaction.atomic():
                if clean["status"] != "occupied":
                    Booking.objects.filter(slot=slot, status="active").update(status="completed", ended_at=timezone.now())
                for field, value in clean.items():
                    setattr(slot, field, value)
                slot.save()
            messages.success(request, f"Slot {clean['label']} updated.")
            return redirect("admin_slots")
    return render(request, "admin_slot_edit.html", {"slot": slot, "form": form, "errors": errors, "types": SLOT_TYPES,
                                                    "statuses": SLOT_STATUSES, "page": "admin_slots"})


@admin_required
@require_POST
def admin_slot_delete(request, slot_id):
    slot = get_object_or_404(Slot, pk=slot_id)
    if Booking.objects.filter(slot=slot, status="active").exists():
        messages.error(request, f"Slot {slot.label} has an active booking. End the booking first.")
    else:
        slot.delete()
        messages.success(request, f"Slot {slot.label} deleted.")
    return redirect("admin_slots")


@admin_required
def admin_bookings(request):
    current = request.GET.get("status", "")
    if current not in ("active", "completed", "cancelled"):
        current = ""
    needle = request.GET.get("q", "").strip()
    rows = Booking.objects.select_related("slot", "user")
    if current:
        rows = rows.filter(status=current)
    if needle:
        rows = rows.filter(Q(name__icontains=needle) | Q(vehicle_number__icontains=needle) | Q(slot__label__icontains=needle))
    return render(request, "admin_bookings.html", {"bookings": rows, "current": current, "query": needle, "page": "admin_bookings"})


@admin_required
@require_POST
def admin_booking_end(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)
    with transaction.atomic():
        changed = Booking.objects.filter(pk=booking_id, status="active").update(status="completed", ended_at=timezone.now())
        if changed:
            Slot.objects.filter(pk=booking.slot_id, status="occupied").update(status="available")
    if changed:
        messages.success(request, f"Booking KB-{booking_id} ended.")
    else:
        messages.error(request, "That booking is not active.")
    return redirect("admin_bookings")
