"""find_nearby_venues.py — the delivery venues near this copy's store, for a person to confirm.

    python3 scripts/find_nearby_venues.py                  # the store's location and radius
    python3 scripts/find_nearby_venues.py --radius-km 3
    python3 scripts/find_nearby_venues.py --listing saved.json --lat 32.1 --lon 34.9

ADR-036 §4. It reads the delivery platform's public retail listing around the store
(configs/store.yaml's location and market.radius_km) and writes the grocery venues within
the radius, nearest first, to a review file. For each it says whether it is already collected
(configs/delivery_targets.yaml) and what format configs/store_types.yaml gives it, if any.

It writes nothing else. A person confirms which venues to collect, adds them to
delivery_targets.yaml, and records each one's format in store_types.yaml as `verified:
manual`, asking when it is not known. A format is never guessed: an unclassified venue is
only ever context (#250).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.store import get_store  # noqa: E402
from src.common.store_types import get_store_types  # noqa: E402
from src.external.venue_discovery import LISTING_URL, fetch_retail_listing, nearby, venues_from_listing  # noqa: E402

TARGETS = ROOT / "configs" / "delivery_targets.yaml"


def _configured_slugs() -> dict[str, str]:
    raw = yaml.safe_load(TARGETS.read_text(encoding="utf-8")) or {}
    return {str(t["url"]).rstrip("/").split("/")[-1]: t.get("key", "")
            for t in raw.get("targets") or [] if t.get("url")}


def main(argv=None) -> int:
    store = get_store()
    parser = argparse.ArgumentParser(description="List the delivery venues near the store, for review.")
    parser.add_argument("--lat", type=float, default=store.location.lat)
    parser.add_argument("--lon", type=float, default=store.location.lon)
    parser.add_argument("--radius-km", type=float, default=store.market_radius_km)
    parser.add_argument("--lines", default="grocery", help="product lines to keep, comma-separated")
    parser.add_argument("--listing", type=Path, default=None, help="a saved listing instead of the live one")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.listing:
        listing, source = json.loads(args.listing.read_text(encoding="utf-8")), str(args.listing)
    else:
        try:
            listing, source = fetch_retail_listing(args.lat, args.lon), f"{LISTING_URL}?lat={args.lat}&lon={args.lon}"
        except Exception as exc:                       # the listing is someone else's service
            print(f"Could not read the retail listing: {exc}", file=sys.stderr)
            return 2

    slugs = _configured_slugs()
    listed = venues_from_listing(listing)
    configured_ids = {v.id for v in listed if v.slug in slugs}
    classified = {sid: rec.store_type for sid, rec in get_store_types().stores.items()}
    venues = nearby(listing, lat=args.lat, lon=args.lon, radius_km=args.radius_km,
                    lines=[line.strip() for line in args.lines.split(",") if line.strip()],
                    configured_ids=configured_ids, classified=classified)
    missing = sorted(key for slug, key in slugs.items() if slug not in {v.slug for v in listed})

    review = {"store_id": store.id, "location": {"lat": args.lat, "lon": args.lon}, "radius_km": args.radius_km,
              "source": source, "read_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "venues": venues, "configured_not_listed": missing,
              "next": "Confirm the venues to collect in configs/delivery_targets.yaml, and record each one's "
                      "format in configs/store_types.yaml as verified: manual. Never guess a format."}
    out = args.out or ROOT / "reports" / "venues" / f"nearby_{store.id}_{review['read_at'][:10]}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{len(venues)} venues within {args.radius_km:g} km of {args.lat}, {args.lon} (lines: {args.lines})")
    for v in venues:
        state = "collected" if v["configured"] else "new"
        print(f"  {v['distance_km']:5.2f} km  {state:9}  {v['format'] or 'no format':16}  {v['name']}")
    if missing:
        print(f"Collected but not in the listing tonight: {', '.join(missing)}")
    print(f"Review file: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
