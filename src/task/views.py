from math import cos, radians, sin, sqrt

from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from src.task.models import Location


# Simple Haversine distance for ordering by proximity.
def _distance_km(lat1, lon1, lat2, lon2):
    radius_km = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    )
    return 2 * radius_km * sqrt(a)


def locations_list(request):
    # Base query with related data and EVSE count.
    locations = Location.objects.select_related("operator", "country").annotate(
        evse_count=Count("evses")
    )

    # optional filters from query params.
    operator = request.GET.get("operator")
    if operator:
        locations = locations.filter(operator__reference=operator)

    country = request.GET.get("country")
    if country:
        locations = locations.filter(country__reference=country)

    # optional ordering, defaulting to reference.
    order = request.GET.get("order")
    if order == "created":
        locations = locations.order_by("created_at")
    elif order == "updated":
        locations = locations.order_by("updated_at")
    elif order == "distance":
        try:
            lat = float(request.GET.get("lat", ""))
            lon = float(request.GET.get("lon", ""))
        except ValueError:
            lat = None
            lon = None

        if lat is not None and lon is not None:
            annotated = []
            for location in locations:
                annotated.append(
                    (
                        _distance_km(
                            lat,
                            lon,
                            float(location.latitude),
                            float(location.longitude),
                        ),
                        location,
                    )
                )
            annotated.sort(key=lambda item: item[0])
            locations = [item[1] for item in annotated]
    else:
        locations = locations.order_by("reference")

    payload = {
        "locations": [
            {
                "coordinates": {
                    "lat": float(location.latitude),
                    "lon": float(location.longitude),
                },
                "operator_reference": location.operator.reference,
                "country_reference": location.country.reference,
                "postal_code": location.postal_code,
                "number_of_evses": location.evse_count,
            }
            for location in locations
        ]
    }

    return JsonResponse(payload)


def location_detail(request, location_reference):
    # Pull one location plus EVSEs and connectors for detail output.
    location = get_object_or_404(
        Location.objects.select_related("operator", "country").prefetch_related(
            "evses__connectors"
        ),
        reference=location_reference,
    )

    evses_payload = []
    for evse in location.evses.all():
        connectors_payload = [
            {"power": connector.power, "standard": connector.standard}
            for connector in evse.connectors.all()
        ]
        evses_payload.append(
            {
                "physical_identifier": evse.physical_identifier,
                "status": evse.status,
                "connectors": connectors_payload,
            }
        )

    payload = {
        "coordinates": {
            "lat": float(location.latitude),
            "lon": float(location.longitude),
        },
        "operator_reference": location.operator.reference,
        "country_reference": location.country.reference,
        "postal_code": location.postal_code,
        "evses": evses_payload,
    }

    return JsonResponse(payload)
