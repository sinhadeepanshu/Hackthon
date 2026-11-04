from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("slots/", views.slots, name="slots"),
    path("api/slots/", views.api_slots, name="api_slots"),
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("book/<int:slot_id>/", views.book, name="book"),
    path("booking/<int:booking_id>/", views.booking_detail, name="booking_detail"),
    path("booking/<int:booking_id>/cancel/", views.cancel, name="cancel"),
    path("my-bookings/", views.my_bookings, name="my_bookings"),
    path("staff/login/", views.admin_login, name="admin_login"),
    path("staff/", views.admin_dashboard, name="admin_dashboard"),
    path("staff/slots/", views.admin_slots, name="admin_slots"),
    path("staff/slots/add/", views.admin_slot_add, name="admin_slot_add"),
    path("staff/slots/<int:slot_id>/edit/", views.admin_slot_edit, name="admin_slot_edit"),
    path("staff/slots/<int:slot_id>/delete/", views.admin_slot_delete, name="admin_slot_delete"),
    path("staff/bookings/", views.admin_bookings, name="admin_bookings"),
    path("staff/bookings/<int:booking_id>/end/", views.admin_booking_end, name="admin_booking_end"),
]
