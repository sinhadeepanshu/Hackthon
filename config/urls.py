from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("django-admin/", admin.site.urls),  # optional built-in Django admin (database level)
    path("", include("parking.urls")),
]
