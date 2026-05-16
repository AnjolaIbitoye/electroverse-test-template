import json
from decimal import Decimal
from pathlib import Path
import tempfile

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from src.task.models import Connector, Country, EVSE, Location, Operator


class LoadIntegratedCommandTests(TestCase):
    def test_load_integrated_persists_data(self):
        # Build a small sample JSON in the new schema.
        sample = [
            {
                "address": "Pennys Walk",
                "city": "Ferndown",
                "coordinates": {"latitude": "50.8011300", "longitude": "-1.8931400"},
                "country": "GBR",
                "name": "Sample Location",
                "id": "LOC-1",
                "postal_code": "E14 5AB",
                "party_id": "OP-1",
                "operator": {"name": "Operator One"},
                "evses": [
                    {
                        "physical_reference": "EVSE-1",
                        "status": "AVAILABLE",
                        "connectors": [
                            {
                                "standard": "IEC_62196_T2",
                                "max_electric_power": 7000,
                                "max_voltage": 230,
                                "max_amperage": 32,
                            }
                        ],
                    }
                ],
            }
        ]

        # Write the sample to a temp file and run the loader.
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as handle:
            json.dump(sample, handle)
            temp_path = Path(handle.name)

        try:
            call_command("load_integrated", path=str(temp_path), reset=True)
        finally:
            temp_path.unlink(missing_ok=True)

        # Verify the data was saved.
        self.assertEqual(Operator.objects.count(), 1)
        self.assertEqual(Country.objects.count(), 1)
        self.assertEqual(Location.objects.count(), 1)
        self.assertEqual(EVSE.objects.count(), 1)
        self.assertEqual(Connector.objects.count(), 1)


class ApiTests(TestCase):
    def setUp(self):
        # Create a small dataset for the API test.
        operator = Operator.objects.create(reference="OP-1", name="Operator One")
        country = Country.objects.create(reference="GBR", name="GBR")
        location = Location.objects.create(
            reference="LOC-1",
            operator=operator,
            country=country,
            postal_code="E14 5AB",
            latitude=Decimal("51.5"),
            longitude=Decimal("-0.12"),
        )
        evse = EVSE.objects.create(
            location=location,
            physical_identifier="EVSE-1",
            status="AVAILABLE",
        )
        Connector.objects.create(evse=evse, power=7, standard="IEC_62196_T2")

    def test_locations_list_endpoint(self):
        # Call the list endpoint and check the response shape.
        url = reverse("locations-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("locations", payload)
        self.assertEqual(len(payload["locations"]), 1)
        self.assertEqual(payload["locations"][0]["number_of_evses"], 1)
