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
        # Read JSON from disk.
        path = Path(options["path"])
        data = json.loads(path.read_text(encoding="utf-8"))

        # Optional full reset before loading.
        if options["reset"]:
            Connector.objects.all().delete()
            EVSE.objects.all().delete()
            Location.objects.all().delete()
            Operator.objects.all().delete()
            Country.objects.all().delete()

        # Support both legacy and new schemas.
        if isinstance(data, dict) and "locations" in data:
            self._load_legacy_schema(data)
        elif isinstance(data, list):
            self._load_new_schema(data)
        else:
            raise ValueError("Unsupported integrated.json schema")

        self.stdout.write(self.style.SUCCESS("Data load complete."))

    def _get_or_create_operator(self, reference: str, name: str) -> Operator:
        operator, _ = Operator.objects.update_or_create(
            reference=reference, defaults={"name": name}
        )
        return operator

    def _get_or_create_country(self, reference: str, name: str) -> Country:
        country, _ = Country.objects.update_or_create(
            reference=reference, defaults={"name": name}
        )
        return country

    def _to_decimal(self, value) -> Decimal:
        # Convert strings or numbers to Decimal safely.
        try:
            return Decimal(str(value))
        except (TypeError, ValueError, ArithmeticError):
            return Decimal("0")

    def _connector_power_kw(self, connector: dict) -> int:
        # Prefer explicit power, otherwise compute from voltage * amperage.
        power = connector.get("max_electric_power")
        if power is None:
            max_voltage = connector.get("max_voltage")
            max_amperage = connector.get("max_amperage")
            if max_voltage is not None and max_amperage is not None:
                try:
                    power = float(max_voltage) * float(max_amperage)
                except (TypeError, ValueError):
                    power = 0
            else:
                power = 0

        try:
            power_value = float(power)
        except (TypeError, ValueError):
            return 0

        if power_value >= 1000:
            return int(round(power_value / 1000))
        return int(round(power_value))

    def _load_legacy_schema(self, data: dict) -> None:
        # Legacy schema has top-level operators/countries/locations.
        operators = {}
        for operator in data.get("operators", []):
            obj = self._get_or_create_operator(
                reference=str(operator["operator_reference"]),
                name=operator.get("name", ""),
            )
            operators[obj.reference] = obj

        countries = {}
        for country in data.get("countries", []):
            obj = self._get_or_create_country(
                reference=str(country["country_reference"]),
                name=country.get("name", ""),
            )
            countries[obj.reference] = obj

        for location in data.get("locations", []):
            operator_ref = str(location["operator_reference"])
            country_ref = str(location["country_reference"])
            operator = operators[operator_ref]
            country = countries[country_ref]

            coords = location.get("coordinates", {})
            latitude = self._to_decimal(coords.get("lat", 0))
            longitude = self._to_decimal(coords.get("lon", 0))

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

    def _load_new_schema(self, data: list) -> None:
        # New schema is a list of locations with nested EVSEs/connectors.
        for index, location in enumerate(data, start=1):
            operator_data = location.get("operator") or {}
            operator_ref = location.get("party_id") or operator_data.get("name")
            if not operator_ref:
                operator_ref = "UNKNOWN"
            operator_name = operator_data.get("name") or operator_ref
            operator = self._get_or_create_operator(str(operator_ref), operator_name)

            country_ref = location.get("country") or "UNKNOWN"
            country = self._get_or_create_country(str(country_ref), str(country_ref))

            coords = location.get("coordinates", {})
            latitude = self._to_decimal(coords.get("latitude", 0))
            longitude = self._to_decimal(coords.get("longitude", 0))

            location_ref = location.get("id") or location.get("name") or str(index)

            loc, _ = Location.objects.update_or_create(
                reference=str(location_ref),
                defaults={
                    "operator": operator,
                    "country": country,
                    "postal_code": location.get("postal_code", ""),
                    "latitude": latitude,
                    "longitude": longitude,
                },
            )

            for evse in location.get("evses", []):
                physical_identifier = (
                    evse.get("physical_reference")
                    or evse.get("uid")
                    or evse.get("evse_id")
                    or ""
                )
                evse_obj, _ = EVSE.objects.update_or_create(
                    location=loc,
                    physical_identifier=str(physical_identifier),
                    defaults={"status": evse.get("status", "UNKNOWN")},
                )
                evse_obj.connectors.all().delete()
                for connector in evse.get("connectors", []):
                    Connector.objects.create(
                        evse=evse_obj,
                        power=self._connector_power_kw(connector),
                        standard=str(connector.get("standard", "UNKNOWN")),
                    )
