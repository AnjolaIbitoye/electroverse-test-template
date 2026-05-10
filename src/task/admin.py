from django.contrib import admin

from src.task.models import Connector, Country, EVSE, Location, Operator


# Show operators in admin with basic search.
@admin.register(Operator)
class OperatorAdmin(admin.ModelAdmin):
    list_display = ("reference", "name")
    search_fields = ("reference", "name")


# Show countries in admin with basic search.
@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("reference", "name")
    search_fields = ("reference", "name")


# Locations list with filters and timestamps.
@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "operator",
        "country",
        "postal_code",
        "created_at",
        "updated_at",
    )
    list_filter = ("operator", "country")
    search_fields = ("reference", "postal_code")


# EVSE list with status filter.
@admin.register(EVSE)
class EVSEAdmin(admin.ModelAdmin):
    list_display = ("physical_identifier", "status", "location")
    list_filter = ("status",)
    search_fields = ("physical_identifier",)


# Connector list with standard filter.
@admin.register(Connector)
class ConnectorAdmin(admin.ModelAdmin):
    list_display = ("standard", "power", "evse")
    list_filter = ("standard",)
