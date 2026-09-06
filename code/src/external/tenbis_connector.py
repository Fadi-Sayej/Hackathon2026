"""
tenbis_connector.py — 10bis (TenBis) delivery catalog collector.

Background
----------
10bis (https://www.10bis.co.il) ships its frontend as a thin React SPA.
The page itself contains NO embedded `__NEXT_DATA__` JSON; the catalogue
loads asynchronously from internal endpoints under `/NextApi/…`.

Two endpoints are used here:

  * GET /NextApi/GetRestaurant?restaurantId=<id>
      Public.  Returns store-level metadata (name, address, city, phone,
      hours, geo coordinates, kosher flags, delivery fees).

  * GET /NextApi/GetRestaurantMenu?RestaurantId=<id>
      **Auth-required.**  The bundled SPA marks this endpoint with
      `isAuthRequired:!0` — without an `Authorization: Bearer <jwt>`
      header the server still returns 200 but with `categoriesList: null`.

Therefore the connector operates in two modes:

  - **Metadata-only mode** (no token):
      Captures store info, writes the empty silver_records, and returns
      an observation count of 0.  Useful for keeping the Firestore
      `stores` collection up-to-date even when no token is available.

  - **Full-menu mode** (TENBIS_BEARER_TOKEN env var set):
      Sends the bearer header and parses the menu sections into
      ExternalProductObservation records.

Headers are tuned to mimic Chrome to mitigate Cloudflare WAF blocking.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from loguru import logger

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.common.raw_storage import save_raw_response
from src.common.schema import ExternalProductObservation


# ── Constants ────────────────────────────────────────────────────────────────

PROVIDER = "tenbis"
SOURCE_ID = "delivery_catalog"         # share the existing source id so the
SOURCE_TYPE = "delivery_catalog"       # data lake layout matches Wolt
TENBIS_API_BASE = "https://www.10bis.co.il/NextApi"

CHROME_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

# Robust browser headers — mitigates Cloudflare WAF.
BROWSER_HEADERS = {
    "user-agent": CHROME_USER_AGENT,
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9,he;q=0.8",
    "accept-encoding": "gzip, deflate, br",
    "origin": "https://www.10bis.co.il",
    "language": "en",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "sec-ch-ua": '"Chromium";v="126", "Not-A.Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
}


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class TenBisStoreInfo:
    provider: str
    source_url: str
    restaurant_id: str
    store_name: Optional[str] = None
    store_name_he: Optional[str] = None
    store_id: Optional[str] = None
    store_chain: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    currency: str = "ILS"
    delivery_fee: Optional[Decimal] = None
    min_order: Optional[Decimal] = None
    is_open_now: Optional[bool] = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class TenBisCollectionResult:
    status: str                          # "ok" | "metadata_only" | "error"
    provider: str
    venue_url: str
    restaurant_id: str
    store_info: TenBisStoreInfo
    observations: list[ExternalProductObservation]
    bronze_records: list[dict[str, Any]]
    raw_paths: list[str]
    notes: list[str]


# ── URL parsing ──────────────────────────────────────────────────────────────

_RESTAURANT_ID_RE = re.compile(r"/restaurants/menu/[^/]+/(\d+)/", re.I)


def extract_restaurant_id(venue_url: str) -> Optional[str]:
    """
    Pull the numeric restaurantId out of a 10bis venue URL.

    >>> extract_restaurant_id(
    ...     "https://www.10bis.co.il/next/en/restaurants/menu/delivery/43548/king-store"
    ... )
    '43548'
    """
    parsed = urlparse(venue_url)
    if "10bis" not in parsed.netloc and "tenbis" not in parsed.netloc:
        return None
    match = _RESTAURANT_ID_RE.search(parsed.path)
    return match.group(1) if match else None


# ── Decimal helpers ──────────────────────────────────────────────────────────

def _to_decimal(value: Any) -> Optional[Decimal]:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except Exception:
        return None


# ── HTTP layer ───────────────────────────────────────────────────────────────

class TenBisClient:
    """Thin wrapper around httpx.Client with TenBis-aware defaults."""

    def __init__(
        self,
        *,
        bearer_token: Optional[str] = None,
        timeout: float = 30.0,
    ):
        headers = dict(BROWSER_HEADERS)
        if bearer_token:
            headers["authorization"] = f"Bearer {bearer_token}"
        self.client = httpx.Client(
            base_url=TENBIS_API_BASE,
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
        )
        self.has_token = bool(bearer_token)
        self.raw_paths: list[str] = []

    def close(self) -> None:
        self.client.close()

    def warm_up(self, venue_url: str, observed_at: datetime) -> None:
        """
        Visit the SPA page once so the server issues a __cf_bm cookie and
        a ShoppingCart GUID before we hit the API.  Cloudflare is far less
        likely to challenge requests that follow a successful page load.
        """
        try:
            with httpx.Client(
                headers={**BROWSER_HEADERS, "accept": "text/html"},
                follow_redirects=True,
                timeout=20,
            ) as page_client:
                response = page_client.get(venue_url)
            # Carry over the cookies onto the API client.
            for cookie in response.cookies.jar:
                self.client.cookies.jar.set_cookie(cookie)
            save_raw_response(
                SOURCE_ID,
                str(response.url),
                "GET",
                response.status_code,
                dict(response.headers),
                response.content,
                response.headers.get("content-type", "text/html"),
                observed_at,
            )
        except Exception as exc:  # warm-up is best-effort
            logger.debug("TenBis warm-up failed (continuing without): {}", exc)

    def fetch_json(
        self,
        endpoint: str,
        params: dict[str, Any],
        observed_at: datetime,
        *,
        referer: str,
    ) -> dict[str, Any]:
        response = self.client.get(
            endpoint,
            params=params,
            headers={"referer": referer},
        )
        body = response.content
        raw_path, _ = save_raw_response(
            SOURCE_ID,
            str(response.url),
            "GET",
            response.status_code,
            dict(response.headers),
            body,
            response.headers.get("content-type", "application/json"),
            observed_at,
        )
        self.raw_paths.append(str(raw_path))
        response.raise_for_status()
        return response.json()


# ── Store info extraction ────────────────────────────────────────────────────

def _store_info_from_restaurant_payload(
    venue_url: str,
    restaurant_id: str,
    payload: dict[str, Any],
) -> TenBisStoreInfo:
    data = payload.get("Data") or {}
    names = data.get("localizationNames") or {}
    info = TenBisStoreInfo(
        provider=PROVIDER,
        source_url=venue_url,
        restaurant_id=restaurant_id,
        store_id=str(data.get("restaurantId") or restaurant_id),
        store_name=names.get("en") or data.get("restaurantName"),
        store_name_he=names.get("he"),
        store_chain=names.get("en") or data.get("restaurantName"),
        city=data.get("restaurantCityName"),
        address=data.get("restaurantAddress"),
        phone=data.get("restaurantPhone"),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        delivery_fee=_to_decimal(data.get("deliveryFeeAmount")),
        min_order=_to_decimal(data.get("minimumPriceForOrder")),
        is_open_now=data.get("isOpenNow"),
        raw={"restaurant": data},
    )
    return info


# ── Menu extraction (auth-only) ──────────────────────────────────────────────

def _iter_menu_items(menu_data: dict[str, Any]):
    """
    Yield (category_name, item_dict, ordered_index) tuples from a 10bis
    restaurant menu payload.

    The 10bis schema (observed):

        Data.categoriesList: [
          {
            "categoryName": "...",
            "dishList": [
              {
                "dishId": int,
                "dishName": str,
                "dishDescription": str,
                "dishPrice": number,
                "dishImageUrl": str,
                "categoryId": int,
                "isActive": bool,
                "isPopular": bool,
                ...
              },
              ...
            ]
          },
          ...
        ]

    The schema is intentionally walked defensively because TenBis grocery
    venues sometimes nest dishes under `subCategoriesList[*].dishList`.
    """
    data = menu_data.get("Data") or menu_data
    categories = data.get("categoriesList") or []
    for category in categories:
        cat_name = category.get("categoryName") or category.get("name")

        for idx, item in enumerate(category.get("dishList") or [], start=1):
            yield cat_name, item, idx

        for sub in category.get("subCategoriesList") or []:
            sub_name = sub.get("categoryName") or sub.get("name") or cat_name
            for idx, item in enumerate(sub.get("dishList") or [], start=1):
                yield sub_name, item, idx


def _observation_from_item(
    *,
    item: dict[str, Any],
    category_name: Optional[str],
    rank_in_category: int,
    store_info: TenBisStoreInfo,
    observed_at: datetime,
    raw_file_path: str,
    venue_url: str,
) -> Optional[ExternalProductObservation]:
    name = item.get("dishName") or item.get("name")
    if not name:
        return None

    dish_id = item.get("dishId") or item.get("id")
    price = _to_decimal(item.get("dishPrice") or item.get("price"))
    original_price = _to_decimal(item.get("originalPrice"))
    sale_price = price if (original_price and price and price < original_price) else None
    regular_price = original_price or price

    is_active = item.get("isActive")
    is_available = item.get("inStock") if "inStock" in item else None
    if is_available is None and isinstance(is_active, bool):
        is_available = is_active

    return ExternalProductObservation(
        source_id=SOURCE_ID,
        observed_at=observed_at,
        barcode=item.get("barcode") or item.get("dishBarcode"),
        sku=str(dish_id) if dish_id is not None else None,
        product_name=name,
        category=category_name,
        unit=item.get("dishUnit") or item.get("unit"),
        price=regular_price,
        sale_price=sale_price,
        currency=store_info.currency or "ILS",
        store_name=store_info.store_name,
        store_id=store_info.store_id,
        store_chain=store_info.store_chain,
        city=store_info.city,
        raw_file_path=raw_file_path,
        source_type=SOURCE_TYPE,
        rank_in_category=rank_in_category,
        most_ordered=bool(item.get("isPopular")) or None,
        source_product_url=venue_url,
        appears_in_price_file=False,
        is_online_available=is_available,
        is_in_catalog=True,
        branch_confidence="high" if store_info.city and store_info.store_id else "medium",
    )


# ── Public entrypoint ────────────────────────────────────────────────────────

def collect_tenbis_venue(
    venue_url: str,
    observed_at: Optional[datetime] = None,
    *,
    bearer_token: Optional[str] = None,
) -> TenBisCollectionResult:
    """
    Scrape a single 10bis venue.

    Parameters
    ----------
    venue_url     : Full 10bis URL of the form
        https://www.10bis.co.il/next/en/restaurants/menu/delivery/<id>/<slug>
    observed_at   : UTC datetime of the collection (defaults to now).
    bearer_token  : Optional `Authorization: Bearer <jwt>` token.  When
        omitted, the connector silently falls back to metadata-only mode
        (TENBIS_BEARER_TOKEN env var is also checked).

    Returns
    -------
    TenBisCollectionResult — see dataclass.
    """
    restaurant_id = extract_restaurant_id(venue_url)
    if not restaurant_id:
        raise ValueError(f"Could not extract restaurantId from URL: {venue_url}")

    observed_at = observed_at or datetime.now(timezone.utc)
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)

    bearer_token = bearer_token or os.environ.get("TENBIS_BEARER_TOKEN") or None
    notes: list[str] = []

    client = TenBisClient(bearer_token=bearer_token)
    try:
        client.warm_up(venue_url, observed_at)

        # 1) Store metadata — always available unauthenticated.
        restaurant_payload = client.fetch_json(
            "/GetRestaurant",
            {"restaurantId": restaurant_id},
            observed_at,
            referer=venue_url,
        )
        store_info = _store_info_from_restaurant_payload(
            venue_url, restaurant_id, restaurant_payload
        )

        # 2) Menu — auth-required.  Fail gracefully without a token.
        observations: list[ExternalProductObservation] = []
        bronze_records: list[dict[str, Any]] = []

        if not client.has_token:
            notes.append(
                "TENBIS_BEARER_TOKEN not set — skipping menu fetch. "
                "Store metadata captured; no item-level observations."
            )
            logger.warning(
                "[tenbis/{}] No bearer token — metadata only.", restaurant_id
            )
            return TenBisCollectionResult(
                status="metadata_only",
                provider=PROVIDER,
                venue_url=venue_url,
                restaurant_id=restaurant_id,
                store_info=store_info,
                observations=observations,
                bronze_records=bronze_records,
                raw_paths=list(client.raw_paths),
                notes=notes,
            )

        menu_payload = client.fetch_json(
            "/GetRestaurantMenu",
            {"RestaurantId": restaurant_id},
            observed_at,
            referer=venue_url,
        )
        # The API answers 200 even when the token is rejected — detect by
        # the categoriesList being None.
        if (menu_payload.get("Data") or {}).get("categoriesList") in (None, []):
            notes.append(
                "GetRestaurantMenu returned an empty categoriesList — "
                "token likely expired or rejected."
            )
            logger.warning(
                "[tenbis/{}] Empty menu — token may be expired.", restaurant_id
            )
            return TenBisCollectionResult(
                status="metadata_only",
                provider=PROVIDER,
                venue_url=venue_url,
                restaurant_id=restaurant_id,
                store_info=store_info,
                observations=observations,
                bronze_records=bronze_records,
                raw_paths=list(client.raw_paths),
                notes=notes,
            )

        raw_menu_path = client.raw_paths[-1] if client.raw_paths else ""

        for category_name, item, rank in _iter_menu_items(menu_payload):
            obs = _observation_from_item(
                item=item,
                category_name=category_name,
                rank_in_category=rank,
                store_info=store_info,
                observed_at=observed_at,
                raw_file_path=raw_menu_path,
                venue_url=venue_url,
            )
            if obs is None:
                continue
            observations.append(obs)
            bronze_records.append({
                "provider": PROVIDER,
                "source_type": SOURCE_TYPE,
                "source_url": venue_url,
                "restaurant_id": restaurant_id,
                "category": category_name,
                "rank_in_category": rank,
                "item": item,
                "store": {
                    "store_id": store_info.store_id,
                    "store_name": store_info.store_name,
                    "store_chain": store_info.store_chain,
                    "city": store_info.city,
                },
            })

        return TenBisCollectionResult(
            status="ok",
            provider=PROVIDER,
            venue_url=venue_url,
            restaurant_id=restaurant_id,
            store_info=store_info,
            observations=observations,
            bronze_records=bronze_records,
            raw_paths=list(client.raw_paths),
            notes=notes,
        )
    finally:
        client.close()
