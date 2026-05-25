"""
delivery_venue_connector.py - Delivery venue catalog collector.

Collects Wolt/TenBis/Cibus/Easy-linked order pages for Alonit / Super Alonit
venues, saves raw HTML and JSON evidence, extracts store-level details, and
normalises visible catalog items to ExternalProductObservation records.

Implemented provider:
  - Wolt venue URLs, including category URLs.

Easy pages are supported as discovery inputs: the connector saves the Easy HTML
and follows visible Wolt venue links. TenBis and Cibus URLs are saved as raw
HTML but currently do not have a catalog extractor.
"""

from __future__ import annotations

import html
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

import httpx
from loguru import logger

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.common.parquet_writer import write_bronze_parquet, write_silver_parquet
from src.common.paths import EXTERNAL_SILVER_ROOT
from src.common.quality import generate_basic_quality_report
from src.common.raw_storage import save_raw_response
from src.common.schema import ExternalProductObservation


SOURCE_ID = "delivery_catalog"
SOURCE_TYPE = "delivery_catalog"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
)
QUERY_STATE_RE = re.compile(
    r'<script[^>]+type=["\']application/json["\'][^>]+class=["\']query-state["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
JSON_LD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
WOLT_LINK_RE = re.compile(r"https://wolt\.com/[^\"'\\\s<>]+/(?:venue|restaurant)/[^\"'\\\s<>]+", re.I)


@dataclass
class RawCapture:
    url: str
    content_type: str
    path: str
    status_code: int


@dataclass
class StoreInfo:
    provider: str
    source_url: str
    store_name: Optional[str] = None
    store_id: Optional[str] = None
    store_chain: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    currency: str = "ILS"
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class DeliveryCollectionResult:
    status: str
    source_id: str
    observed_at: str
    input_urls: list[str]
    resolved_venue_urls: list[str]
    store_infos: list[dict[str, Any]]
    total_observations: int
    raw_capture_count: int
    bronze_path: Optional[str]
    silver_path: Optional[str]
    store_info_path: Optional[str]
    quality_report_path: str
    unsupported_urls: list[str]


def _provider_for_url(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "wolt.com" in host:
        return "wolt"
    if "easy.co.il" in host:
        return "easy"
    if "10bis" in host or "tenbis" in host:
        return "tenbis"
    if "cibus" in host:
        return "cibus"
    return "unknown"


def _canonical_wolt_venue_url(url: str) -> str:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if "venue" not in parts and "restaurant" not in parts:
        return url

    marker = "venue" if "venue" in parts else "restaurant"
    idx = parts.index(marker)
    if idx + 1 >= len(parts):
        return url

    base_parts = parts[: idx + 2]
    return f"{parsed.scheme}://{parsed.netloc}/{'/'.join(base_parts)}"


def _wolt_slug(url: str) -> Optional[str]:
    parts = [part for part in urlparse(url).path.split("/") if part]
    for marker in ("venue", "restaurant"):
        if marker in parts:
            idx = parts.index(marker)
            if idx + 1 < len(parts):
                return parts[idx + 1]
    return None


def _category_url(base_venue_url: str, category_slug: str) -> str:
    return f"{_canonical_wolt_venue_url(base_venue_url)}/items/{category_slug}"


def _decimal_from_minor_units(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return (Decimal(str(value)) / Decimal("100")).quantize(Decimal("0.01"))
    except Exception:
        return None


def _extract_query_state(html_text: str) -> Optional[dict[str, Any]]:
    match = QUERY_STATE_RE.search(html_text)
    if not match:
        return None
    return json.loads(html.unescape(match.group(1)))


def _query_data(query_state: dict[str, Any], key_prefix: list[Any]) -> list[Any]:
    matches: list[Any] = []
    for query in query_state.get("queries", []):
        query_key = query.get("queryKey") or []
        if query_key[: len(key_prefix)] == key_prefix:
            data = query.get("state", {}).get("data")
            if data is not None:
                matches.append(data)
    return matches


def _all_json_ld(html_text: str) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for match in JSON_LD_RE.finditer(html_text):
        try:
            parsed = json.loads(html.unescape(match.group(1)))
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            docs.append(parsed)
    return docs


def _flatten_categories(categories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for category in categories:
        flattened.append(category)
        flattened.extend(_flatten_categories(category.get("subcategories") or []))
    return flattened


def _extract_category_slugs(query_state: dict[str, Any]) -> list[str]:
    slugs: list[str] = []
    seen: set[str] = set()
    for data in _query_data(query_state, ["venue-assortment", "category-listing"]):
        for category in _flatten_categories(data.get("categories") or []):
            slug = category.get("slug")
            item_ids = category.get("item_ids") or []
            if slug and slug not in seen and (item_ids or category.get("subcategories")):
                seen.add(slug)
                slugs.append(slug)
    return slugs


def _extract_most_ordered_item_ids(query_state: dict[str, Any]) -> set[str]:
    item_ids: set[str] = set()
    for data in _query_data(query_state, ["venue-assortment", "venue-content"]):
        for page in data.get("pages", []):
            for section in page.get("sections", []):
                section_name = f"{section.get('name') or ''} {section.get('slug') or ''}".lower()
                if "most ordered" not in section_name and "popular" not in section_name:
                    continue
                for category in section.get("categories") or []:
                    item_ids.update(category.get("item_ids") or [])
    return item_ids


def _store_info_from_wolt(
    url: str,
    html_text: str,
    query_state: Optional[dict[str, Any]],
) -> StoreInfo:
    info = StoreInfo(provider="wolt", source_url=url)

    for doc in _all_json_ld(html_text):
        if doc.get("@type") != "Store":
            continue
        address = doc.get("address") or {}
        geo = doc.get("geo") or {}
        info.store_name = doc.get("name") or info.store_name
        info.address = address.get("streetAddress") or info.address
        info.city = address.get("addressLocality") or info.city
        info.phone = doc.get("telephone") or info.phone
        info.latitude = geo.get("latitude") or info.latitude
        info.longitude = geo.get("longitude") or info.longitude
        info.raw["json_ld_store"] = doc

    if query_state:
        for data in _query_data(query_state, ["venue", "static"]):
            venue = data.get("venue") or {}
            info.store_id = venue.get("id") or info.store_id
            info.store_name = venue.get("name") or info.store_name
            info.store_chain = venue.get("brand_name") or info.store_chain
            info.city = venue.get("city") or info.city
            info.address = venue.get("address") or info.address
            info.currency = venue.get("currency") or info.currency
            info.raw["static_venue"] = venue

    return info


def _availability_from_item(item: dict[str, Any]) -> Optional[bool]:
    if item.get("disabled_info") is not None:
        return False
    if item.get("purchasable_balance") == 0:
        return False
    return True


def _extract_category_items(
    query_state: dict[str, Any],
    *,
    store_info: StoreInfo,
    observed_at: datetime,
    raw_file_path: str,
    page_url: str,
    most_ordered_ids: set[str],
) -> tuple[list[ExternalProductObservation], list[dict[str, Any]]]:
    observations: list[ExternalProductObservation] = []
    bronze_records: list[dict[str, Any]] = []

    category_pages = _query_data(query_state, ["venue-assortment", "category"])
    for data in category_pages:
        for page in data.get("pages", []):
            category = page.get("category") or {}
            category_name = category.get("name")
            ordered_ids: list[str] = []
            for category_ref in page.get("categories") or []:
                ordered_ids.extend(category_ref.get("item_ids") or [])
            rank_lookup = {
                item_id: idx + 1
                for idx, item_id in enumerate(ordered_ids)
            }

            for idx, item in enumerate(page.get("items") or [], start=1):
                name = item.get("name")
                if not name:
                    continue

                product_id = item.get("id")
                original_price = _decimal_from_minor_units(item.get("original_price"))
                price = _decimal_from_minor_units(item.get("price"))
                promo_price = price if original_price and price and price < original_price else None
                regular_price = original_price or price

                obs = ExternalProductObservation(
                    source_id=SOURCE_ID,
                    observed_at=observed_at,
                    barcode=item.get("barcode_gtin"),
                    sku=product_id,
                    product_name=name,
                    category=category_name,
                    unit=item.get("unit_info"),
                    price=regular_price,
                    sale_price=promo_price,
                    currency=store_info.currency or "ILS",
                    price_per_unit=_decimal_from_minor_units((item.get("unit_price") or {}).get("price")),
                    store_name=store_info.store_name,
                    store_id=store_info.store_id,
                    store_chain=store_info.store_chain,
                    city=store_info.city,
                    raw_file_path=raw_file_path,
                    source_type=SOURCE_TYPE,
                    rank_in_category=rank_lookup.get(product_id, idx),
                    most_ordered=True if product_id in most_ordered_ids else None,
                    source_product_url=page_url,
                    appears_in_price_file=False,
                    is_online_available=_availability_from_item(item),
                    is_in_catalog=True,
                )
                observations.append(obs)
                bronze_records.append(
                    {
                        "provider": "wolt",
                        "source_type": SOURCE_TYPE,
                        "source_url": page_url,
                        "store": store_info.__dict__,
                        "category": category,
                        "rank_in_category": rank_lookup.get(product_id, idx),
                        "most_ordered": product_id in most_ordered_ids,
                        "item": item,
                    }
                )

    return observations, bronze_records


class DeliveryVenueConnector:
    def __init__(self, *, timeout: float = 30.0):
        self.client = httpx.Client(
            follow_redirects=True,
            timeout=timeout,
            headers={
                "user-agent": DEFAULT_USER_AGENT,
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
                "accept-language": "en,he;q=0.9",
            },
        )
        self.raw_captures: list[RawCapture] = []
        self.unsupported_urls: list[str] = []

    def close(self) -> None:
        self.client.close()

    def _fetch_and_save(
        self,
        url: str,
        observed_at: datetime,
        *,
        raise_for_status: bool = True,
    ) -> tuple[httpx.Response, str]:
        response = self.client.get(url)
        content_type = response.headers.get("content-type", "")
        raw_path, _ = save_raw_response(
            SOURCE_ID,
            str(response.url),
            "GET",
            response.status_code,
            dict(response.headers),
            response.content,
            content_type,
            observed_at,
        )
        self.raw_captures.append(
            RawCapture(str(response.url), content_type, str(raw_path), response.status_code)
        )
        if raise_for_status:
            response.raise_for_status()
        return response, str(raw_path)

    def _save_query_state(
        self,
        source_url: str,
        query_state: dict[str, Any],
        observed_at: datetime,
    ) -> str:
        body = json.dumps(query_state, ensure_ascii=False, indent=2).encode("utf-8")
        raw_path, _ = save_raw_response(
            SOURCE_ID,
            f"{source_url}#query-state",
            "GET",
            200,
            {"content-type": "application/json; charset=utf-8"},
            body,
            "application/json; charset=utf-8",
            observed_at,
        )
        self.raw_captures.append(
            RawCapture(f"{source_url}#query-state", "application/json; charset=utf-8", str(raw_path), 200)
        )
        return str(raw_path)

    def discover_venue_urls(self, input_urls: list[str], observed_at: datetime) -> list[str]:
        venue_urls: list[str] = []
        seen: set[str] = set()

        for url in input_urls:
            provider = _provider_for_url(url)
            if provider == "wolt":
                canonical = _canonical_wolt_venue_url(url)
                if canonical not in seen:
                    seen.add(canonical)
                    venue_urls.append(canonical)
                continue

            response, _ = self._fetch_and_save(url, observed_at, raise_for_status=False)
            if response.status_code >= 400:
                logger.warning(
                    "Could not inspect linked order page (status={}): {}",
                    response.status_code,
                    url,
                )
                self.unsupported_urls.append(url)
                continue
            if provider == "easy":
                for match in WOLT_LINK_RE.findall(response.text):
                    canonical = _canonical_wolt_venue_url(html.unescape(match))
                    if canonical not in seen:
                        seen.add(canonical)
                        venue_urls.append(canonical)
            else:
                self.unsupported_urls.append(url)

        return venue_urls

    def collect_wolt_venue(
        self,
        venue_url: str,
        observed_at: datetime,
        *,
        max_categories: Optional[int] = None,
    ) -> tuple[StoreInfo, list[ExternalProductObservation], list[dict[str, Any]]]:
        response, _ = self._fetch_and_save(venue_url, observed_at)
        query_state = _extract_query_state(response.text)
        if not query_state:
            raise ValueError(f"Wolt page did not include query-state JSON: {venue_url}")

        self._save_query_state(str(response.url), query_state, observed_at)
        store_info = _store_info_from_wolt(str(response.url), response.text, query_state)
        most_ordered_ids = _extract_most_ordered_item_ids(query_state)
        category_slugs = _extract_category_slugs(query_state)

        if not category_slugs:
            slug = _wolt_slug(str(response.url))
            logger.warning("No category listing found for Wolt venue slug={}", slug)

        selected_slugs = category_slugs[:max_categories] if max_categories else category_slugs
        observations: list[ExternalProductObservation] = []
        bronze_records: list[dict[str, Any]] = []

        for category_slug in selected_slugs:
            page_url = _category_url(str(response.url), category_slug)
            category_response, _ = self._fetch_and_save(page_url, observed_at)
            category_state = _extract_query_state(category_response.text)
            if not category_state:
                logger.warning("No query-state JSON found on category page: {}", page_url)
                continue
            category_raw_path = self._save_query_state(str(category_response.url), category_state, observed_at)
            page_observations, page_bronze = _extract_category_items(
                category_state,
                store_info=store_info,
                observed_at=observed_at,
                raw_file_path=category_raw_path,
                page_url=str(category_response.url),
                most_ordered_ids=most_ordered_ids,
            )
            observations.extend(page_observations)
            bronze_records.extend(page_bronze)

        return store_info, observations, bronze_records


def _dedupe_observations(
    observations: list[ExternalProductObservation],
) -> list[ExternalProductObservation]:
    deduped: list[ExternalProductObservation] = []
    seen: set[tuple[str, str, str]] = set()
    for obs in observations:
        key = (
            obs.store_id or obs.store_name or "",
            obs.barcode or obs.sku or obs.product_name,
            obs.category or "",
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(obs)
    return deduped


def run_delivery_venue_collection(
    venue_urls: list[str],
    *,
    observed_at: Optional[datetime] = None,
    max_categories: Optional[int] = None,
) -> DeliveryCollectionResult:
    if not venue_urls:
        raise ValueError("At least one venue/order URL is required")

    observed_at = observed_at or datetime.now(timezone.utc)
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)

    connector = DeliveryVenueConnector()
    try:
        resolved_urls = connector.discover_venue_urls(venue_urls, observed_at)
        all_store_infos: list[StoreInfo] = []
        all_observations: list[ExternalProductObservation] = []
        all_bronze_records: list[dict[str, Any]] = []

        for resolved_url in resolved_urls:
            provider = _provider_for_url(resolved_url)
            if provider != "wolt":
                connector.unsupported_urls.append(resolved_url)
                continue
            logger.info("Collecting Wolt delivery catalog: {}", resolved_url)
            store_info, observations, bronze_records = connector.collect_wolt_venue(
                resolved_url,
                observed_at,
                max_categories=max_categories,
            )
            all_store_infos.append(store_info)
            all_observations.extend(observations)
            all_bronze_records.extend(bronze_records)

        all_observations = _dedupe_observations(all_observations)
        silver_records = [
            obs.model_dump(mode="json")
            for obs in all_observations
        ]

        bronze_path = write_bronze_parquet(all_bronze_records, SOURCE_ID, observed_at)
        silver_path = write_silver_parquet(
            silver_records,
            "products",
            observed_at,
            source_id=SOURCE_ID,
        )
        store_info_records = [info.__dict__ for info in all_store_infos]
        store_info_path = (
            EXTERNAL_SILVER_ROOT
            / "stores"
            / SOURCE_ID
            / observed_at.strftime("%Y/%m/%d")
            / f"stores_{observed_at.strftime('%Y%m%dT%H%M%S')}_silver.json"
        )
        store_info_path.parent.mkdir(parents=True, exist_ok=True)
        store_info_path.write_text(
            json.dumps(store_info_records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        quality_path = generate_basic_quality_report(silver_records, SOURCE_ID, observed_at)

        return DeliveryCollectionResult(
            status="ok",
            source_id=SOURCE_ID,
            observed_at=observed_at.isoformat(),
            input_urls=venue_urls,
            resolved_venue_urls=resolved_urls,
            store_infos=store_info_records,
            total_observations=len(silver_records),
            raw_capture_count=len(connector.raw_captures),
            bronze_path=str(bronze_path),
            silver_path=str(silver_path),
            store_info_path=str(store_info_path),
            quality_report_path=str(quality_path),
            unsupported_urls=connector.unsupported_urls,
        )
    finally:
        connector.close()
