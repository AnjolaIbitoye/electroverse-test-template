from django.urls import path

from src.task import views


# API routes for the task app.
urlpatterns = [
    path("", views.locations_list, name="locations-list"),
    path("<str:location_reference>/", views.location_detail, name="location-detail"),
]
