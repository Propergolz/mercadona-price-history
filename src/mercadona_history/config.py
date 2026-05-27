from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Location:
    location_id: str
    province: str
    postal_code: str


DEFAULT_LOCATIONS = [
    Location(location_id="valencia_46001", province="Valencia", postal_code="46001"),
]

