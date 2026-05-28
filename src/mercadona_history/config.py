from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Location:
    location_id: str
    province: str
    postal_code: str


DEFAULT_LOCATIONS = [
    Location(location_id="madrid_28001", province="Madrid", postal_code="28001"),
    Location(location_id="barcelona_08001", province="Barcelona", postal_code="08001"),
    Location(location_id="valencia_46001", province="Valencia", postal_code="46001"),
    Location(location_id="alicante_03001", province="Alicante", postal_code="03001"),
    Location(location_id="sevilla_41001", province="Sevilla", postal_code="41001"),
]

