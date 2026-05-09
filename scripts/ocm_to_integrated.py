#!/usr/bin/env python
"""Convert Open Charge Map POI data into the integrated.json schema."""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


def load_records(raw: Any) -> List[Dict[str, Any]]:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        data = raw.get("data")
        if isinstance(data, list):
            return data
    raise ValueError("Unsupported input format: expected list or {data: [...]}.")


def map_status(status_id: Any) -> str:
    if status_id == 50:
        return "AVAILABLE"
    if status_id in (0, None):
        return "UNKNOWN"
    return "UNKNOWN"


def map_standard(connection: Dict[str, Any]) -> str:
    connection_type_id = connection.get("ConnectionTypeID")
    if connection_type_id is None:
        return "UNKNOWN"
    return f"TYPE_ID_{connection_type_id}"


def map_power(connection: Dict[str, Any]) -> int:
    power_kw = connection.get("PowerKW")
    if power_kw is None:
        return 0
    try:
        return int(round(float(power_kw)))
    except (TypeError, ValueError):
        return 0


def operator_reference(item: Dict[str, Any]) -> str:
    operator_id = item.get("OperatorID")
    if operator_id is not None:
        return str(operator_id)
    operator_info = item.get("OperatorInfo") or {}
    operator_info_id = operator_info.get("ID")
    if operator_info_id is not None:
        return str(operator_info_id)
    return "UNKNOWN"


def operator_name(item: Dict[str, Any], ref: str) -> str:
    operator_info = item.get("OperatorInfo") or {}
    name = operator_info.get("Title")
    if name:
        return str(name)
    return f"Operator {ref}"


def country_reference(address: Dict[str, Any]) -> str:
    country_id = address.get("CountryID")
    if country_id is not None:
        return str(country_id)
    return "UNKNOWN"


def country_name(address: Dict[str, Any], ref: str) -> str:
    country = address.get("Country") or {}
    name = country.get("Title")
    if name:
        return str(name)
    return f"Country {ref}"


def location_reference(item: Dict[str, Any]) -> str:
    uuid = item.get("UUID")
    if uuid:
        return str(uuid)
    item_id = item.get("ID")
    if item_id is not None:
        return str(item_id)
    return "UNKNOWN"


def build_output(records: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    operators: Dict[str, Dict[str, Any]] = {}
    countries: Dict[str, Dict[str, Any]] = {}
    locations: List[Dict[str, Any]] = []

    for item in records:
        address = item.get("AddressInfo") or {}
        lat = address.get("Latitude")
        lon = address.get("Longitude")
        if lat is None or lon is None:
            continue

        op_ref = operator_reference(item)
        operators.setdefault(
            op_ref, {"operator_reference": op_ref, "name": operator_name(item, op_ref)}
        )

        country_ref = country_reference(address)
        countries.setdefault(
            country_ref,
            {"country_reference": country_ref, "name": country_name(address, country_ref)},
        )

        loc_ref = location_reference(item)
        connections = item.get("Connections") or []
        evses: List[Dict[str, Any]] = []

        for idx, connection in enumerate(connections, start=1):
            physical_identifier = connection.get("Reference")
            if not physical_identifier:
                physical_identifier = f"{loc_ref}-evse-{idx}"

            connector = {
                "power": map_power(connection),
                "standard": map_standard(connection),
            }

            evses.append(
                {
                    "physical_identifier": str(physical_identifier),
                    "status": map_status(
                        connection.get("StatusTypeID") or item.get("StatusTypeID")
                    ),
                    "connectors": [connector],
                }
            )

        locations.append(
            {
                "location_reference": loc_ref,
                "operator_reference": op_ref,
                "country_reference": country_ref,
                "postal_code": address.get("Postcode") or "",
                "coordinates": {"lat": float(lat), "lon": float(lon)},
                "evses": evses,
            }
        )

    return {
        "operators": list(operators.values()),
        "countries": list(countries.values()),
        "locations": locations,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert Open Charge Map data to integrated.json schema."
    )
    parser.add_argument(
        "--input",
        default="integrated_raw.json",
        help="Path to OCM JSON (default: integrated_raw.json)",
    )
    parser.add_argument(
        "--output",
        default="integrated.json",
        help="Path to write converted JSON (default: integrated.json)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    raw = json.loads(input_path.read_text(encoding="utf-8"))
    records = load_records(raw)
    converted = build_output(records)

    output_path.write_text(
        json.dumps(converted, indent=2, sort_keys=False), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
