"""
schema.py — Pydantic models for the YomYom market-intelligence pipeline.

All models use Pydantic v2.  Fields are Optional where the data source may
not always provide a value; validators normalise common issues (whitespace,
empty strings → None).

Models
------
  ExternalProductObservation  — one product seen at a competitor / external source.
  InternalPOSProduct          — one product line from the YomYom POS CSV.
  ProductRecommendation       — a reorder or sourcing recommendation.
  PlanogramRecommendation     — where a product should be placed on the shelf.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ── Shared validators ──────────────────────────────────────────────────────────

def _empty_str_to_none(v: Optional[str]) -> Optional[str]:
    if isinstance(v, str) and not v.strip():
        return None
    return v.strip() if isinstance(v, str) else v


# ── External product observation ───────────────────────────────────────────────

class ExternalProductObservation(BaseModel):
    """
    A single product observation scraped / downloaded from an external source
    (Wolt venue, Shufersal catalogue, price-transparency XML, etc.).
    """

    # Identity
    source_id: str = Field(..., description="Collector identifier, e.g. 'wolt', 'shufersal'.")
    observed_at: datetime = Field(..., description="UTC timestamp when this record was fetched.")
    barcode: Optional[str] = Field(None, description="GTIN-8/12/13/14 or internal SKU.")
    sku: Optional[str] = Field(None, description="Retailer-internal SKU.")

    # Product info
    product_name: str = Field(..., description="Product name as seen at the source.")
    brand: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    unit: Optional[str] = Field(None, description="Unit of measure, e.g. '1L', '500g'.")
    country_of_origin: Optional[str] = None

    # Pricing
    price: Optional[Decimal] = Field(None, description="Shelf price in ILS.")
    sale_price: Optional[Decimal] = Field(None, description="Promotional price in ILS.")
    currency: str = Field("ILS", description="ISO 4217 currency code.")
    price_per_unit: Optional[Decimal] = None

    # Source location
    store_name: Optional[str] = None
    store_id: Optional[str] = None
    store_chain: Optional[str] = None
    city: Optional[str] = None

    # Raw reference
    raw_file_path: Optional[str] = Field(
        None, description="Path to the raw file this record was extracted from."
    )

    @field_validator("barcode", "sku", "product_name", "brand", "category",
                     "subcategory", "unit", "store_name", "store_id",
                     "store_chain", "city", mode="before")
    @classmethod
    def strip_empty(cls, v):
        return _empty_str_to_none(v)

    @field_validator("price", "sale_price", "price_per_unit", mode="before")
    @classmethod
    def parse_price(cls, v):
        if v is None or v == "":
            return None
        try:
            return Decimal(str(v))
        except Exception:
            return None

    model_config = {"str_strip_whitespace": True}


# ── Internal POS product ───────────────────────────────────────────────────────

class InternalPOSProduct(BaseModel):
    """
    One product / SKU row from the YomYom POS CSV export.
    Field names mirror common Israeli POS formats (Comax / Priority).
    """

    # Identity
    barcode: Optional[str] = None
    sku: Optional[str] = None
    product_name: str

    # Category
    category: Optional[str] = None
    subcategory: Optional[str] = None
    department: Optional[str] = None

    # Pricing & cost
    selling_price: Optional[Decimal] = None
    cost_price: Optional[Decimal] = None
    vat_included: bool = True

    # Inventory
    stock_qty: Optional[Decimal] = None
    min_stock_qty: Optional[Decimal] = None
    reorder_qty: Optional[Decimal] = None

    # Sales (aggregated from POS lines)
    units_sold_30d: Optional[int] = None
    revenue_30d: Optional[Decimal] = None
    last_sale_date: Optional[date] = None

    # Supplier
    supplier_name: Optional[str] = None
    supplier_sku: Optional[str] = None

    # Timestamps
    pos_export_date: Optional[date] = None

    @field_validator("barcode", "sku", "product_name", "category",
                     "subcategory", "department", "supplier_name",
                     "supplier_sku", mode="before")
    @classmethod
    def strip_empty(cls, v):
        return _empty_str_to_none(v)

    @field_validator("selling_price", "cost_price", "stock_qty",
                     "min_stock_qty", "reorder_qty", "revenue_30d", mode="before")
    @classmethod
    def parse_decimal(cls, v):
        if v is None or v == "":
            return None
        try:
            return Decimal(str(v))
        except Exception:
            return None

    model_config = {"str_strip_whitespace": True}


# ── Product recommendation ─────────────────────────────────────────────────────

class ProductRecommendation(BaseModel):
    """
    A reorder, sourcing, or pricing recommendation for a specific product.
    Generated by the recommendation engine; stored in data/recommendations/.
    """

    recommendation_id: str = Field(..., description="UUID or deterministic hash.")
    generated_at: datetime

    # Subject
    barcode: Optional[str] = None
    sku: Optional[str] = None
    product_name: str

    # Type
    recommendation_type: Literal[
        "reorder", "stop_ordering", "price_increase", "price_decrease",
        "new_product", "delist", "supplier_switch"
    ]

    # Quantities & values
    suggested_order_qty: Optional[Decimal] = None
    suggested_price: Optional[Decimal] = None
    expected_margin_pct: Optional[float] = None
    priority_score: float = Field(0.0, ge=0.0, le=1.0)

    # Rationale
    reason: str = Field(..., description="Human-readable explanation.")
    supporting_signals: list[str] = Field(
        default_factory=list,
        description="Signal keys that drove this recommendation.",
    )

    # Status
    status: Literal["pending", "approved", "rejected", "snoozed"] = "pending"
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None

    model_config = {"str_strip_whitespace": True}


# ── Planogram recommendation ───────────────────────────────────────────────────

class PlanogramRecommendation(BaseModel):
    """
    Where and how a product should be placed on the physical shelf.
    One row = one product placement.
    """

    planogram_id: str = Field(..., description="Unique ID for this planogram version.")
    generated_at: datetime

    # Product identity
    barcode: Optional[str] = None
    sku: Optional[str] = None
    product_name: str

    # Physical placement
    shelf_id: str = Field(..., description="Shelf / gondola identifier.")
    tier: int = Field(..., ge=1, description="Shelf tier from bottom (1 = bottom).")
    position: int = Field(..., ge=1, description="Position from left on the tier.")
    facings: int = Field(1, ge=1, description="Number of product facings.")
    depth: int = Field(1, ge=1, description="Units stacked back-to-front.")

    # Visual
    facing_width_cm: Optional[float] = None
    facing_height_cm: Optional[float] = None

    # Category zone
    category: Optional[str] = None
    zone_label: Optional[str] = Field(
        None, description="E.g. 'eye_level', 'grab_zone', 'floor_level'."
    )

    # Score
    placement_score: float = Field(0.0, ge=0.0, le=1.0)
    reason: Optional[str] = None

    # Status
    status: Literal["draft", "approved", "active", "archived"] = "draft"

    model_config = {"str_strip_whitespace": True}
