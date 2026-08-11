"""
alonit_connector.py — Dor Alon / Alonit price-transparency collector.

Downloads Stores, PriceFull, and PromoFull XML.gz files from the Israeli
mandatory price-transparency FTP server (publishedprices.co.il), filters
for Alonit branches in Kafr Qasim (כפר קאסם) and Super Alonit Einat (עינת),
and normalises records to ExternalProductObservation.

Public FTP server (no password required):
  Host     : url.retail.publishedprices.co.il
  Username : doralon
  Password : (empty string)
  Protocol : FTP port 21

Pipeline
--------
  1. Connect to FTP.
  2. Download Stores XML.gz → identify target store IDs.
  3. Download PromoFull XML.gz for target stores → build promo-price map.
  4. Download PriceFull XML.gz for target stores → normalise items with promos.
  5. Write bronze + silver Parquet via the common layer.
  6. Generate quality report.

Usage (library)
---------------
    from src.external.alonit_connector import run_alonit_collection

    result = run_alonit_collection()
    # result == {"status": "ok", "stores_found": [...], "total_observations": N, ...}

Usage (CLI)
-----------
    python scripts/run_alonit_collector.py
    python scripts/run_alonit_collector.py --no-save-raw
"""

from __future__ import annotations

import fnmatch
import ftplib
import ssl
import gzip
import io
import json
import re
import sys
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional
import xml.etree.ElementTree as ET

import httpx
from loguru import logger

# ── Project root on sys.path ──────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.common.paths import get_quality_report_path
from src.common.raw_storage import save_raw_file, save_raw_response
from src.common.parquet_writer import write_bronze_parquet, write_silver_parquet
from src.common.schema import ExternalProductObservation


# ── Constants ─────────────────────────────────────────────────────────────────

SOURCE_ID = "alonit"

FTP_HOST    = "url.retail.publishedprices.co.il"
FTP_USER    = "doralon"
FTP_PASS    = ""
FTP_TIMEOUT = 30   # seconds per FTP operation
PORTAL_BASE_URL = "https://url.retail.publishedprices.co.il"

# Target stores — Hebrew and English spellings seen in store metadata.
TARGET_KAFR_QASIM_TERMS = {
    "כפר קאסם",
    "kafr qasim",
    "kfar qasim",
    "al-madina 2",
    "al madina 2",
    "אל מדינה 2",
}
TARGET_EINAT_TERMS = {
    "עינת",
    "einat",
}

# FTP file-name patterns (case-insensitive fnmatch)
_PAT_STORES = "*store*"
_PAT_PRICE  = "*pricef*"
_PAT_PROMO  = "*promof*"


# ─────────────────────────────────────────────────────────────────────────────
# FTP helpers
# ─────────────────────────────────────────────────────────────────────────────

class _ReusingFTP_TLS(ftplib.FTP_TLS):
    """FTPS client for the Israeli price-transparency servers.

    Two non-obvious requirements, both of which look like a firewall block when
    missing — the connection authenticates, then NLST hangs until it times out:

    1. TLS SESSION REUSE on the data channel. The server refuses a data
       connection that negotiates a fresh session.

    2. TRUSTING THE PASV ADDRESS. The service sits behind several IPs: the
       control connection lands on 194.90.26.22 while PASV directs data to
       194.90.26.21. Python (and modern curl) ignore the PASV-reported address
       by default as an anti-spoofing measure and reconnect to the control host,
       where nothing is listening on that port. Here the mismatch is real
       infrastructure, not an attack, so the address is trusted — see
       `trust_server_pasv_ipv4_address` in `_ftp_connect`.
    """

    def ntransfercmd(self, cmd, rest=None):
        conn, size = ftplib.FTP.ntransfercmd(self, cmd, rest)
        if self._prot_p:
            conn = self.context.wrap_socket(
                conn, server_hostname=self.host, session=self.sock.session
            )
        return conn, size


def _ftp_connect() -> ftplib.FTP:
    """Open and return an authenticated FTP connection."""
    logger.info("Connecting to FTP  user={}  host={}", FTP_USER, FTP_HOST)
    ftp = ftplib.FTP()
    try:
        ftp.connect(host=FTP_HOST, port=21, timeout=FTP_TIMEOUT)
        ftp.login(user=FTP_USER, passwd=FTP_PASS)
        ftp.set_pasv(True)
        logger.info("FTP connected: {!r}", ftp.getwelcome())
        return ftp
    except ftplib.error_perm as exc:
        try:
            ftp.close()
        except Exception:
            pass
        if "secure connection required" not in str(exc).casefold():
            raise

    logger.info("FTP server requires TLS; retrying with explicit FTPS")
    # The server's certificate does not match its hostname. It serves public
    # price data with no credentials, so verification is relaxed deliberately
    # rather than silently — there is nothing confidential to protect here.
    context = ssl._create_unverified_context()
    ftps = _ReusingFTP_TLS(context=context)
    ftps.connect(host=FTP_HOST, port=21, timeout=FTP_TIMEOUT)
    ftps.login(user=FTP_USER, passwd=FTP_PASS)
    ftps.prot_p()
    ftps.set_pasv(True)
    ftps.trust_server_pasv_ipv4_address = True
    logger.info("FTPS connected: {!r}", ftps.getwelcome())
    return ftps


def _ftp_list(ftp: ftplib.FTP, pattern: str) -> list[str]:
    """
    List files matching *pattern* (case-insensitive fnmatch).

    Tries server-side NLST glob first; falls back to listing all files and
    filtering client-side so both behaviours are handled.
    """
    pat_lower = pattern.lower()
    try:
        files = ftp.nlst(pattern)
        if files:
            return files
    except (ftplib.error_perm, TimeoutError, OSError) as exc:
        logger.debug("NLST {} failed in current mode: {}", pattern, exc)
        try:
            ftp.set_pasv(False)
            files = ftp.nlst(pattern)
            if files:
                return files
        except (ftplib.error_perm, TimeoutError, OSError) as active_exc:
            logger.debug("NLST {} failed in active mode: {}", pattern, active_exc)
        finally:
            try:
                ftp.set_pasv(True)
            except Exception:
                pass
    # Fallback: list everything and filter client-side
    try:
        all_files = ftp.nlst()
        return [f for f in all_files if fnmatch.fnmatch(f.lower(), pat_lower)]
    except (ftplib.error_perm, TimeoutError, OSError) as exc:
        logger.debug("Full NLST fallback failed: {}", exc)
        return []


def _ftp_download(ftp: ftplib.FTP, filename: str) -> bytes:
    """Download *filename* into an in-memory BytesIO buffer and return bytes."""
    buf = io.BytesIO()
    ftp.retrbinary(f"RETR {filename}", buf.write)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# Cerberus web portal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _portal_client() -> tuple[httpx.Client, str]:
    """
    Log into Dor Alon's Cerberus web portal and return (client, csrf_token).

    The public FTP endpoint may require TLS and fail on data-channel listings in
    some environments. The same files are exposed through the Cerberus web UI.
    """
    client = httpx.Client(
        verify=False,
        follow_redirects=True,
        timeout=60,
        headers={"user-agent": "Mozilla/5.0"},
    )
    login = client.get(f"{PORTAL_BASE_URL}/login")
    login.raise_for_status()
    match = re.search(r'csrftoken" content="([^"]+)"', login.text)
    if not match:
        client.close()
        raise RuntimeError("CSRF token not found on Dor Alon portal login page")

    csrf = match.group(1)
    response = client.post(
        f"{PORTAL_BASE_URL}/login/user",
        data={
            "username": FTP_USER,
            "password": FTP_PASS,
            "r": "/file",
            "csrftoken": csrf,
        },
        headers={"Referer": f"{PORTAL_BASE_URL}/login"},
    )
    response.raise_for_status()

    file_page = client.get(f"{PORTAL_BASE_URL}/file")
    file_page.raise_for_status()
    match = re.search(r'csrftoken" content="([^"]+)"', file_page.text)
    return client, match.group(1) if match else csrf


def _portal_list_files(client: httpx.Client, csrf: str) -> list[dict]:
    all_files: list[dict] = []
    page_size = 500
    start = 0
    echo = 1
    while True:
        response = client.post(
            f"{PORTAL_BASE_URL}/file/json/dir",
            data={
                "sEcho": echo,
                "iDisplayStart": start,
                "iDisplayLength": page_size,
                "csrftoken": csrf,
            },
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"{PORTAL_BASE_URL}/file",
            },
        )
        response.raise_for_status()
        payload = response.json()
        batch = payload.get("aaData", [])
        all_files.extend(batch)
        total = int(payload.get("iTotalRecords") or len(all_files))
        if not batch or len(all_files) >= total:
            break
        start += page_size
        echo += 1
    return all_files


def _portal_download_file(client: httpx.Client, filename: str) -> httpx.Response:
    response = client.get(f"{PORTAL_BASE_URL}/file/d/{filename}")
    response.raise_for_status()
    return response


# ─────────────────────────────────────────────────────────────────────────────
# XML helpers
# ─────────────────────────────────────────────────────────────────────────────

def _parse_xml_gz(data: bytes) -> ET.Element:
    """
    Decompress gzip bytes (or use as-is if not compressed), decode, and parse.

    Tries UTF-8, UTF-8-BOM, Windows-1255, and ISO-8859-8 in order, because
    Israeli price-transparency files use different encodings across chains.
    """
    try:
        xml_bytes = gzip.decompress(data)
    except OSError:
        xml_bytes = data  # already plain XML

    for enc in ("utf-8", "utf-8-sig", "utf-16-le", "windows-1255", "iso-8859-8"):
        try:
            return ET.fromstring(xml_bytes.decode(enc))
        except (UnicodeDecodeError, ET.ParseError):
            continue

    raise ValueError("Could not decode/parse XML — tried utf-8, utf-8-sig, windows-1255, iso-8859-8")


def _gtext(element: Optional[ET.Element], *tags: str, default: str = "") -> str:
    """
    Return the stripped text of the first matching child tag.

    Accepts multiple candidate tag names to handle minor XML format variations
    between Stores versions (e.g. 'StoreId' vs 'StoreID').
    """
    if element is None:
        return default
    for tag in tags:
        child = element.find(tag)
        if child is not None and child.text:
            return child.text.strip()
    return default


def _gdecimal(element: Optional[ET.Element], *tags: str) -> Optional[Decimal]:
    """Extract a Decimal value from one of several candidate child tags."""
    raw = _gtext(element, *tags)
    if not raw:
        return None
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Stores parser
# ─────────────────────────────────────────────────────────────────────────────

def parse_stores(root: ET.Element) -> list[dict]:
    """
    Parse an Israeli-format Stores XML root into a flat list of store dicts.

    Handles two common layouts:
      Layout A (most chains):  root/SubChains/SubChain/Stores/Store
      Layout B (older format): root/Stores/Branch
    """
    stores: list[dict] = []

    # Layout A
    for store_el in root.findall(".//SubChain//Store"):
        stores.append({
            "store_id":   _gtext(store_el, "StoreId", "StoreID"),
            "store_name": _gtext(store_el, "StoreName", "StoreName2"),
            "address":    _gtext(store_el, "Address"),
            "city":       _gtext(store_el, "City"),
            "zip_code":   _gtext(store_el, "ZipCode", "ZIPCode"),
            "store_type": _gtext(store_el, "StoreType"),
        })

    # Layout B fallback
    if not stores:
        for branch in root.findall(".//Branch"):
            stores.append({
                "store_id":   _gtext(branch, "StoreID", "StoreId"),
                "store_name": _gtext(branch, "StoreName"),
                "address":    _gtext(branch, "Address"),
                "city":       _gtext(branch, "City"),
                "zip_code":   _gtext(branch, "ZipCode"),
                "store_type": "",
            })

    # Last-resort: direct Store children of root
    if not stores:
        for store_el in root.findall(".//Store"):
            stores.append({
                "store_id":   _gtext(store_el, "StoreId", "StoreID"),
                "store_name": _gtext(store_el, "StoreName"),
                "address":    _gtext(store_el, "Address"),
                "city":       _gtext(store_el, "City"),
                "zip_code":   _gtext(store_el, "ZipCode"),
                "store_type": _gtext(store_el, "StoreType"),
            })

    return stores


def filter_target_stores(stores: list[dict], all_stores: bool = False) -> dict[str, dict]:
    """
    Return {store_id: store_info}, by default only Kafr Qasim and Einat.

    TWO DIFFERENT QUESTIONS NEED TWO DIFFERENT STORE SETS
    ----------------------------------------------------
    *Price comparison* asks "what does the shop down the road charge?" — three
    nearby branches, which is what the default gives.

    *Latent-state inference* (#49) asks "is the chain dropping this product?"
    A delisting is a chain-wide decision, so telling one apart from an ordinary
    stockout needs chain-wide visibility. Measured on the 3-branch snapshot:
    75.6% of products appeared at a single branch and only 6.0% at all three,
    so the concentration test had statistical power on 6% of the catalog and
    reported UNCERTAIN for the rest. The chain publishes 156 stores.

    `all_stores=True` keeps every branch, for the snapshot. Nothing downstream
    of the price comparison changes: `target_label` is still set for the two
    named locations, so existing consumers filter exactly as before.
    """
    result: dict[str, dict] = {}
    for s in stores:
        sid  = s.get("store_id", "").strip()
        city = s.get("city", "")
        name = s.get("store_name", "")
        address = s.get("address", "")
        haystack = f"{city} {name} {address}".casefold()
        if not sid:
            continue
        is_kafr_qasim = any(term.casefold() in haystack for term in TARGET_KAFR_QASIM_TERMS)
        is_einat = any(term.casefold() in haystack for term in TARGET_EINAT_TERMS)
        if is_kafr_qasim or is_einat:
            result[sid] = s
            result[sid]["target_label"] = (
                "alonit_kafr_qasim" if is_kafr_qasim else "super_alonit_einat"
            )
            logger.info(
                "Target store found: target={} id={!r}  name={!r}  city={!r}",
                result[sid]["target_label"], sid, name, city,
            )
        elif all_stores:
            # Kept for chain-wide inference, but deliberately left without a
            # target_label so nothing that filters on one starts picking these up.
            result[sid] = s
            result[sid]["target_label"] = None
    if all_stores:
        labelled = sum(1 for s in result.values() if s.get("target_label"))
        logger.info(
            "Chain-wide collection: {} stores ({} named targets, {} additional)",
            len(result), labelled, len(result) - labelled,
        )
    return result


# ─────────────────────────────────────────────────────────────────────────────
# PriceFull parser
# ─────────────────────────────────────────────────────────────────────────────

def parse_price_full(root: ET.Element) -> tuple[str, list[dict]]:
    """
    Parse a PriceFull XML root.

    Returns
    -------
    (store_id, items)  where each item dict has keys:
      item_code, item_name, manufacturer, unit_of_measure,
      quantity, item_price, unit_price
    """
    store_id = _gtext(root, "StoreId", "StoreID")
    items: list[dict] = []

    for item in root.findall(".//Item"):
        item_name = _gtext(item, "ItemName")
        if not item_name:
            continue
        items.append({
            "item_code":       _gtext(item, "ItemCode"),
            "item_name":       item_name,
            "manufacturer":    _gtext(item, "ManufacturerName", "ManufacturerItemDescription"),
            "unit_of_measure": _gtext(item, "UnitOfMeasure", "UnitQty"),
            "quantity":        _gtext(item, "Quantity"),
            "item_price":      _gdecimal(item, "ItemPrice"),
            "unit_price":      _gdecimal(item, "UnitOfMeasurePrice"),
        })

    return store_id, items


# ─────────────────────────────────────────────────────────────────────────────
# PromoFull parser
# ─────────────────────────────────────────────────────────────────────────────

def parse_promo_full(root: ET.Element) -> tuple[str, dict[str, Decimal]]:
    """
    Parse a PromoFull XML root.

    Returns
    -------
    (store_id, {item_code: discounted_price})

    Only active (non-expired) single-item promotions with a clear numeric
    DiscountedPrice are included.  Complex bundle / multi-item promos are
    skipped to avoid emitting incorrect unit prices.
    """
    store_id = _gtext(root, "StoreId", "StoreID")
    promo_prices: dict[str, Decimal] = {}
    today = date.today().isoformat()

    for sale in root.findall(".//Sale"):
        end_date = _gtext(sale, "EndDate")
        if end_date and end_date < today:
            continue  # expired promo — skip

        for item in sale.findall(".//Item"):
            code = _gtext(item, "ItemCode")
            if not code:
                continue
            disc = _gdecimal(item, "DiscountedPrice", "ItemPrice")
            if disc is not None and disc > 0:
                promo_prices[code] = disc  # last promo for this code wins

    return store_id, promo_prices


# ─────────────────────────────────────────────────────────────────────────────
# Normalizer
# ─────────────────────────────────────────────────────────────────────────────

def normalize_items(
    price_items: list[dict],
    promo_prices: dict[str, Decimal],
    store_info: dict,
    observed_at: datetime,
    raw_file_path: Optional[str],
) -> list[ExternalProductObservation]:
    """
    Convert raw price-file item dicts to ExternalProductObservation instances.

    Parameters
    ----------
    price_items    : Dicts from parse_price_full().
    promo_prices   : {item_code: discounted_price} from parse_promo_full().
    store_info     : Store metadata dict from filter_target_stores().
    observed_at    : Collection timestamp (UTC).
    raw_file_path  : Filename of the source PriceFull file (for lineage).
    """
    observations: list[ExternalProductObservation] = []

    for item in price_items:
        item_name = (item.get("item_name") or "").strip()
        if not item_name:
            continue

        code       = item.get("item_code") or None
        shelf_price = item.get("item_price")
        sale_p     = promo_prices.get(code) if code else None

        # Determine branch confidence: Alonit FTP data always has store_id + name + city
        has_store_id   = bool(store_info.get("store_id"))
        has_store_name = bool(store_info.get("store_name"))
        has_city       = bool(store_info.get("city"))
        if has_store_id and has_store_name and has_city:
            _branch_conf = "high"
        elif has_store_id or has_store_name:
            _branch_conf = "medium"
        else:
            _branch_conf = "low"

        obs = ExternalProductObservation(
            source_id   = SOURCE_ID,
            observed_at = observed_at,
            barcode     = code,
            sku         = code,
            product_name = item_name,
            brand        = item.get("manufacturer") or None,
            unit         = item.get("unit_of_measure") or None,
            price        = shelf_price,
            sale_price   = sale_p,
            currency     = "ILS",
            store_id     = store_info.get("store_id") or None,
            store_name   = store_info.get("store_name") or None,
            store_chain  = "Alonit",
            city         = store_info.get("city") or None,
            raw_file_path = raw_file_path,
            # Collector-level classification flags
            appears_in_price_file = True,
            is_online_available   = None,   # price files carry no availability signal
            is_in_catalog         = True,
            source_type           = "price_file",
            branch_confidence     = _branch_conf,
        )
        observations.append(obs)

    return observations


# ─────────────────────────────────────────────────────────────────────────────
# Quality report
# ─────────────────────────────────────────────────────────────────────────────

def generate_alonit_quality_report(
    observations: list[ExternalProductObservation],
    stores_found: dict[str, dict],
    total_promo_count: int,
    observed_at: datetime,
) -> Path:
    """
    Write a JSON quality report for this Alonit collection run.

    Metrics:
      row_count, stores_found, unique_stores_in_obs, unique_products,
      products_per_store, promo_count, with_promo_price,
      missing_barcode_count/pct, missing_price_count/pct.
    """
    total = len(observations)
    missing_barcode  = sum(1 for o in observations if not o.barcode)
    missing_price    = sum(1 for o in observations if o.price is None)
    with_promo       = sum(1 for o in observations if o.sale_price is not None)
    unique_products  = len({o.barcode for o in observations if o.barcode})
    unique_stores    = len({o.store_id for o in observations if o.store_id})

    per_store: dict[str, int] = {}
    for obs in observations:
        sid = obs.store_id or "unknown"
        per_store[sid] = per_store.get(sid, 0) + 1

    report = {
        "source_id":              SOURCE_ID,
        "observed_at":            observed_at.isoformat(),
        "row_count":              total,
        "stores_found": [
            {
                "store_id":   k,
                "store_name": v.get("store_name"),
                "city":       v.get("city"),
            }
            for k, v in stores_found.items()
        ],
        "unique_stores_in_obs":   unique_stores,
        "unique_products":        unique_products,
        "products_per_store":     per_store,
        "promo_count":            total_promo_count,
        "with_promo_price":       with_promo,
        "missing_barcode_count":  missing_barcode,
        "missing_barcode_pct":    round(missing_barcode / total * 100, 2) if total else 0,
        "missing_price_count":    missing_price,
        "missing_price_pct":      round(missing_price / total * 100, 2) if total else 0,
    }

    report_path = get_quality_report_path(SOURCE_ID, observed_at.isoformat())
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("Quality report: {}", report_path)
    return report_path


# ─────────────────────────────────────────────────────────────────────────────
# Cerberus web-portal collection path
# ─────────────────────────────────────────────────────────────────────────────

def discover_portal_price_files() -> dict:
    """
    Discover Dor Alon Stores / PriceFull / PromoFull files through the web portal.
    Returns counts and samples without downloading or parsing product files.
    """
    client, csrf = _portal_client()
    try:
        files = _portal_list_files(client, csrf)
    finally:
        client.close()

    stores = [f for f in files if f.get("fname", "").startswith("Stores")]
    pricefull = [f for f in files if f.get("fname", "").startswith("PriceFull")]
    promofull = [f for f in files if f.get("fname", "").startswith("PromoFull")]
    return {
        "portal_base_url": PORTAL_BASE_URL,
        "total_files_count": len(files),
        "stores_files_count": len(stores),
        "pricefull_files_count": len(pricefull),
        "promofull_files_count": len(promofull),
        "stores_files_sample": [f.get("fname") for f in stores[:10]],
        "pricefull_files_sample": [f.get("fname") for f in pricefull[:10]],
        "promofull_files_sample": [f.get("fname") for f in promofull[:10]],
    }


def _latest_file(files: list[dict]) -> Optional[dict]:
    if not files:
        return None
    return sorted(files, key=lambda f: f.get("time") or f.get("fname") or "")[-1]


def _latest_files_by_store(files: list[dict]) -> dict[str, dict]:
    by_store: dict[str, dict] = {}
    for file_info in files:
        fname = file_info.get("fname", "")
        match = re.search(r"-(\d+)-(\d{8})-", fname)
        if not match:
            continue
        store_id = match.group(1)
        existing = by_store.get(store_id)
        if existing is None or (file_info.get("time") or fname) > (existing.get("time") or existing.get("fname") or ""):
            by_store[store_id] = file_info
    return by_store


def _save_portal_response(
    *,
    response: httpx.Response,
    filename: str,
    observed_at: datetime,
) -> Path:
    raw_path, _ = save_raw_response(
        source_id=SOURCE_ID,
        url=f"{PORTAL_BASE_URL}/file/d/{filename}",
        method="GET",
        status_code=response.status_code,
        headers=dict(response.headers),
        body=response.content,
        content_type=response.headers.get("content-type") or "application/octet-stream",
        observed_at=observed_at,
    )
    return raw_path


def run_alonit_portal_collection(
    save_raw: bool = True,
    observed_at: Optional[datetime] = None,
) -> dict:
    """
    Run Dor Alon collection through the Cerberus web portal.

    This is the preferred path when the FTP endpoint accepts login but cannot
    open data-channel listings from the current environment.
    """
    if observed_at is None:
        observed_at = datetime.now(tz=timezone.utc)
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)
    obs_ts = observed_at.isoformat()

    client, csrf = _portal_client()
    try:
        files = _portal_list_files(client, csrf)
        store_files = [f for f in files if f.get("fname", "").startswith("Stores")]
        price_files = [f for f in files if f.get("fname", "").startswith("PriceFull")]
        promo_files = [f for f in files if f.get("fname", "").startswith("PromoFull")]

        stores_file = _latest_file(store_files)
        if not stores_file:
            return {
                "status": "error",
                "reason": "No Stores files found in Dor Alon portal",
                "file_discovery": discover_portal_price_files(),
            }

        stores_fname = stores_file["fname"]
        stores_response = _portal_download_file(client, stores_fname)
        stores_raw_path = (
            _save_portal_response(response=stores_response, filename=stores_fname, observed_at=observed_at)
            if save_raw else None
        )
        stores_root = _parse_xml_gz(stores_response.content)
        stores = parse_stores(stores_root)
        target_stores = filter_target_stores(stores, all_stores=all_stores)

        price_by_store = _latest_files_by_store(price_files)
        promo_by_store_files = _latest_files_by_store(promo_files)
        promo_by_store: dict[str, dict[str, Decimal]] = {}
        all_observations: list[ExternalProductObservation] = []
        total_promo_count = 0

        for store_id, store_info in target_stores.items():
            promo_info = promo_by_store_files.get(store_id)
            if promo_info:
                promo_response = _portal_download_file(client, promo_info["fname"])
                if save_raw:
                    _save_portal_response(
                        response=promo_response,
                        filename=promo_info["fname"],
                        observed_at=observed_at,
                    )
                promo_store_id, promo_prices = parse_promo_full(_parse_xml_gz(promo_response.content))
                if promo_store_id == store_id:
                    promo_by_store[store_id] = promo_prices
                    total_promo_count += len(promo_prices)

            price_info = price_by_store.get(store_id)
            if not price_info:
                logger.warning("No PriceFull file found for target store {}", store_id)
                continue

            price_response = _portal_download_file(client, price_info["fname"])
            price_raw_path = (
                _save_portal_response(
                    response=price_response,
                    filename=price_info["fname"],
                    observed_at=observed_at,
                )
                if save_raw else None
            )
            parsed_store_id, price_items = parse_price_full(_parse_xml_gz(price_response.content))
            if parsed_store_id != store_id:
                logger.warning(
                    "Skipping PriceFull {} because parsed store_id={} expected={}",
                    price_info["fname"], parsed_store_id, store_id,
                )
                continue

            observations = normalize_items(
                price_items=price_items,
                promo_prices=promo_by_store.get(store_id, {}),
                store_info=store_info,
                observed_at=observed_at,
                raw_file_path=str(price_raw_path or price_info["fname"]),
            )
            all_observations.extend(observations)

        records = [obs.model_dump(mode="json") for obs in all_observations]
        bronze_path = None
        silver_path = None
        if records:
            bronze_path = write_bronze_parquet(records, SOURCE_ID, obs_ts)
            silver_path = write_silver_parquet(records, "alonit_prices", obs_ts, source_id=SOURCE_ID)

        quality_path = generate_alonit_quality_report(
            observations=all_observations,
            stores_found=target_stores,
            total_promo_count=total_promo_count,
            observed_at=observed_at,
        )

        found_labels = {store.get("target_label") for store in target_stores.values()}
        return {
            "status": "ok",
            "collection_method": "cerberus_web_portal",
            "stores_file": stores_fname,
            "stores_raw_path": str(stores_raw_path) if stores_raw_path else None,
            "stores_found": list(target_stores.keys()),
            "target_labels_found": sorted(label for label in found_labels if label),
            "missing_target_labels": sorted(
                {"alonit_kafr_qasim", "super_alonit_einat"} - {label for label in found_labels if label}
            ),
            "total_observations": len(all_observations),
            "total_promo_count": total_promo_count,
            "bronze_path": str(bronze_path) if bronze_path else None,
            "silver_path": str(silver_path) if silver_path else None,
            "quality_report_path": str(quality_path),
            "file_discovery": {
                "stores_files_count": len(store_files),
                "pricefull_files_count": len(price_files),
                "promofull_files_count": len(promo_files),
            },
        }
    except Exception as exc:
        logger.exception("Dor Alon portal collection failed: {}", exc)
        return {"status": "error", "reason": str(exc), "collection_method": "cerberus_web_portal"}
    finally:
        client.close()


# ─────────────────────────────────────────────────────────────────────────────
# Main collection pipeline
# ─────────────────────────────────────────────────────────────────────────────

def run_alonit_collection(
    save_raw: bool = True,
    observed_at: Optional[datetime] = None,
    all_stores: bool = False,
) -> dict:
    """
    Run the full Alonit price-transparency collection pipeline.

    Steps
    -----
    1. Connect to FTP.
    2. Download Stores file  → identify target store IDs (Kafr Qasim / Einat).
    3. Download PromoFull files for target stores → build promo-price map.
    4. Download PriceFull files for target stores → normalise with promo data.
    5. Write bronze + silver Parquet.
    6. Generate quality report.

    Parameters
    ----------
    save_raw    : If True, persist every downloaded file via save_raw_file().
    observed_at : Override the collection timestamp (default: UTC now).

    Returns
    -------
    dict  with keys: status, stores_found, total_observations,
                     total_promo_count, quality_report_path
          On error:  status="error", reason=<str>
    """
    if observed_at is None:
        observed_at = datetime.now(tz=timezone.utc)

    obs_ts = observed_at.isoformat()
    logger.info("=== Alonit collection started at {} ===", obs_ts)

    # ── 1. Connect ────────────────────────────────────────────────────────────
    try:
        ftp = _ftp_connect()
    except (ftplib.all_errors, OSError) as exc:
        logger.error("FTP connection failed: {}", exc)
        return {"status": "error", "reason": f"FTP connection failed: {exc}"}

    target_stores: dict[str, dict]              = {}
    promo_by_store: dict[str, dict[str, Decimal]] = {}
    all_observations: list[ExternalProductObservation] = []
    total_promo_count = 0

    try:
        # ── 2. Stores file ────────────────────────────────────────────────────
        store_files = _ftp_list(ftp, _PAT_STORES)
        logger.info("Stores files on FTP: {}", store_files)

        for fname in store_files:
            logger.info("Downloading stores file: {}", fname)
            try:
                data = _ftp_download(ftp, fname)
            except ftplib.all_errors as exc:
                logger.warning("Download failed {}: {}", fname, exc)
                continue

            if save_raw:
                save_raw_file(
                    source_id=SOURCE_ID,
                    original_filename=fname,
                    file_bytes=data,
                    observed_at=obs_ts,
                    source_url=f"ftp://{FTP_HOST}/{fname}",
                )

            try:
                root = _parse_xml_gz(data)
            except Exception as exc:
                logger.warning("Parse failed {}: {}", fname, exc)
                continue

            stores = parse_stores(root)
            logger.info("  {} stores in {}", len(stores), fname)
            target_stores.update(filter_target_stores(stores, all_stores=all_stores))

        if not target_stores:
            logger.warning(
                "No target stores found (Kafr Qasim terms={!r}, Einat terms={!r}). "
                "Observations will be empty.",
                TARGET_KAFR_QASIM_TERMS, TARGET_EINAT_TERMS,
            )

        # ── 3. PromoFull files ────────────────────────────────────────────────
        promo_files = _ftp_list(ftp, _PAT_PROMO)
        logger.info("PromoFull files on FTP: {}", promo_files)

        for fname in promo_files:
            logger.info("Downloading promo file: {}", fname)
            try:
                data = _ftp_download(ftp, fname)
            except ftplib.all_errors as exc:
                logger.warning("Download failed {}: {}", fname, exc)
                continue

            try:
                root = _parse_xml_gz(data)
            except Exception as exc:
                logger.warning("Parse failed {}: {}", fname, exc)
                continue

            store_id, promo_prices = parse_promo_full(root)

            if store_id not in target_stores:
                logger.debug("Skipping promo file {} (store {} not a target)", fname, store_id)
                continue

            # Save raw only for target stores
            if save_raw:
                save_raw_file(
                    source_id=SOURCE_ID,
                    original_filename=fname,
                    file_bytes=data,
                    observed_at=obs_ts,
                    source_url=f"ftp://{FTP_HOST}/{fname}",
                )

            promo_by_store[store_id] = promo_prices
            total_promo_count += len(promo_prices)
            logger.info(
                "  {} promo prices for store {} ({})",
                len(promo_prices), store_id,
                target_stores[store_id].get("store_name", "?"),
            )

        # ── 4. PriceFull files ────────────────────────────────────────────────
        price_files = _ftp_list(ftp, _PAT_PRICE)
        logger.info("PriceFull files on FTP: {}", price_files)

        for fname in price_files:
            logger.info("Downloading price file: {}", fname)
            try:
                data = _ftp_download(ftp, fname)
            except ftplib.all_errors as exc:
                logger.warning("Download failed {}: {}", fname, exc)
                continue

            try:
                root = _parse_xml_gz(data)
            except Exception as exc:
                logger.warning("Parse failed {}: {}", fname, exc)
                continue

            store_id, price_items = parse_price_full(root)

            if store_id not in target_stores:
                logger.debug("Skipping price file {} (store {} not a target)", fname, store_id)
                continue

            if save_raw:
                save_raw_file(
                    source_id=SOURCE_ID,
                    original_filename=fname,
                    file_bytes=data,
                    observed_at=obs_ts,
                    source_url=f"ftp://{FTP_HOST}/{fname}",
                )

            store_info   = target_stores[store_id]
            promo_prices = promo_by_store.get(store_id, {})

            obs_list = normalize_items(
                price_items=price_items,
                promo_prices=promo_prices,
                store_info=store_info,
                observed_at=observed_at,
                raw_file_path=fname,
            )
            all_observations.extend(obs_list)
            logger.info(
                "  {} observations for store {} ({}) from {}",
                len(obs_list), store_id,
                store_info.get("store_name", "?"),
                fname,
            )

    except Exception as exc:
        logger.error("Unexpected error during collection: {}", exc, exc_info=True)
        return {"status": "error", "reason": str(exc)}

    finally:
        try:
            ftp.quit()
        except Exception:
            ftp.close()
        logger.info("FTP connection closed")

    # ── 5. Write Parquet ──────────────────────────────────────────────────────
    if all_observations:
        records = [obs.model_dump(mode="json") for obs in all_observations]
        try:
            write_bronze_parquet(records, SOURCE_ID, obs_ts)
            write_silver_parquet(records, "alonit_prices", obs_ts, source_id=SOURCE_ID)
            logger.info("Parquet files written ({} rows)", len(records))
        except Exception as exc:
            logger.error("Parquet write failed: {}", exc)
    else:
        logger.warning("No observations — skipping Parquet write")

    # ── 6. Quality report ─────────────────────────────────────────────────────
    qr_path = generate_alonit_quality_report(
        observations=all_observations,
        stores_found=target_stores,
        total_promo_count=total_promo_count,
        observed_at=observed_at,
    )

    logger.info(
        "=== Alonit collection complete — {} observations, {} target stores ===",
        len(all_observations), len(target_stores),
    )

    return {
        "status":              "ok",
        "stores_found":        list(target_stores.keys()),
        "total_observations":  len(all_observations),
        "total_promo_count":   total_promo_count,
        "quality_report_path": str(qr_path),
    }
