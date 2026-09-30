"""venue_discovery.py — the delivery venues near a store (ADR-036 §4).

A new store's nearby market is found from its location, not built by hand. This reads the
delivery platform's public retail listing around a point and measures each venue's distance.
A person then confirms which venues to collect (configs/delivery_targets.yaml) and states each
one's format (configs/store_types.yaml, `verified: manual`). Nothing here writes either file,
and nothing here guesses a format: an unclassified venue is only ever context (#250).
"""
from __future__ import annotations

import json
import math
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Iterable, Mapping, Optional

LISTING_URL = "https://consumer-api.wolt.com/v1/pages/retail"
VENUE_URL = "https://wolt.com/en/isr/{city}/venue/{slug}"


@dataclass(frozen=True)
class Venue:
    id: str
    name: str
    slug: str
    lat: float
    lon: float
    product_line: str
    address: str
    franchise: str
    url: str


def fetch_retail_listing(lat: float, lon: float, *, timeout: float = 30.0) -> dict:
    """The platform's retail listing around a point. Raises on a network or HTTP failure."""
    query = urllib.parse.urlencode({"lat": lat, "lon": lon})
    request = urllib.request.Request(f"{LISTING_URL}?{query}", headers={"User-Agent": "smartshelf/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def venues_from_listing(listing: Mapping) -> list[Venue]:
    """Every venue the listing carries, once each. A venue without a location is skipped."""
    city = listing.get("city") or ""
    seen: dict[str, Venue] = {}
    for section in listing.get("sections") or []:
        for item in section.get("items") or []:
            v = (item or {}).get("venue") or {}
            location = v.get("location") or []
            if not v.get("id") or len(location) != 2 or v["id"] in seen:
                continue
            lon, lat = float(location[0]), float(location[1])      # the listing gives [lon, lat]
            slug = v.get("slug") or ""
            seen[v["id"]] = Venue(
                id=str(v["id"]), name=v.get("name") or "", slug=slug, lat=lat, lon=lon,
                product_line=v.get("product_line") or "", address=v.get("address") or "",
                franchise=v.get("franchise") or "", url=VENUE_URL.format(city=city, slug=slug))
    return list(seen.values())


def nearby(listing: Mapping, *, lat: float, lon: float, radius_km: float,
           lines: Iterable[str] = ("grocery",), configured_ids: Iterable[str] = (),
           classified: Optional[Mapping[str, str]] = None) -> list[dict]:
    """The venues within the radius, nearest first.

    Kept: every venue of the given product lines, and every venue already configured whatever
    its line. `format` is the format store_types.yaml already gives the venue, or None.
    """
    lines, configured, classified = set(lines), set(configured_ids), dict(classified or {})
    out = []
    for v in venues_from_listing(listing):
        distance = haversine_km(lat, lon, v.lat, v.lon)
        if distance > radius_km or (v.product_line not in lines and v.id not in configured):
            continue
        out.append({"id": v.id, "name": v.name, "distance_km": round(distance, 2),
                    "product_line": v.product_line, "franchise": v.franchise, "address": v.address,
                    "url": v.url, "configured": v.id in configured, "format": classified.get(v.id)})
    return sorted(out, key=lambda row: (row["distance_km"], row["id"]))
