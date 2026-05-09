from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from src.task.models import Connector, Country, EVSE, Location, Operator


class Command(BaseCommand):
    help = "Load integrated.json data into the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default="integrated.json",
            help="Path to integrated.json (default: integrated.json)",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing data before loading",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        path = Path(options["path"])
        data = json.loads(path.read_text(encoding="utf-8"))

        if options["reset"]:
            Connector.objects.all().delete()
            EVSE.objects.all().delete()
            Location.objects.all().delete()
            Operator.objects.all().delete()
            Country.objects.all().delete()

        operators = {}
        for operator in data.get("operators", []):
            obj, _ = Operator.objects.update_or_create(
                reference=str(operator["operator_reference"]),
                defaults={"name": operator.get("name", "")},
            )
            operators[obj.reference] = obj

        countries = {}
        for country in data.get("countries", []):
            obj, _ = Country.objects.update_or_create(
                reference=str(country["country_reference"]),
                defaults={"name": country.get("name", "")},
            )
            countries[obj.reference] = obj

        for location in data.get("locations", []):
            operator_ref = str(location["operator_reference"])
            country_ref = str(location["country_reference"])
            operator = operators[operator_ref]
            country = countries[country_ref]

            coords = location.get("coordinates", {})
            latitude = Decimal(str(coords.get("lat", 0)))
            longitude = Decimal(str(coords.get("lon", 0)))

            loc, _ = Location.objects.update_or_create(
                reference=str(location["location_reference"]),
                defaults={
                    "operator": operator,
                    "country": country,
                    "postal_code": location.get("postal_code", ""),
                    "latitude": latitude,
                    "longitude": longitude,
                },
            )

            for evse in location.get("evses", []):
                evse_obj, _ = EVSE.objects.update_or_create(
                    location=loc,
                    physical_identifier=str(evse.get("physical_identifier", "")),
                    defaults={"status": evse.get("status", "UNKNOWN")},
                )
                evse_obj.connectors.all().delete()
                for connector in evse.get("connectors", []):
                    Connector.objects.create(
                        evse=evse_obj,
                        power=int(connector.get("power", 0)),
                        standard=str(connector.get("standard", "UNKNOWN")),
                    )

        self.stdout.write(self.style.SUCCESS("Data load complete."))