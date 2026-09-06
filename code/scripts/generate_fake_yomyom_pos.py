"""
generate_fake_yomyom_pos.py
===========================
Generate a realistic fake POS CSV for YomYom market, Kafr Qasim.

Produces ~130 product rows that simulate the kinds of data issues,
stock patterns, and margin profiles found in a real neighborhood-store
POS export — without using any real store data.

Intentional "dirt" in the output
---------------------------------
- ~8 % of rows have a missing barcode.
- ~13 % of rows have a missing supplier.
- 4 deliberate duplicate product-name pairs (data-entry errors).
- Some fast-moving products with critically low stock.
- Some dead-stock products with high quantity and near-zero sales.
- High-margin impulse items (energy drinks, imported chocolate, candy).
- Low-margin essentials (milk, water, bread, cooking oil).

Output
------
  data/internal/raw_pos/yomyom/sample_yomyom_pos.csv

Usage
-----
  python scripts/generate_fake_yomyom_pos.py
"""

from __future__ import annotations

import csv
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

# ── project root on sys.path ──────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from loguru import logger

# ── reproducibility ───────────────────────────────────────────────────────────
import random
_RNG = random.Random(42)

# ── anchor date ───────────────────────────────────────────────────────────────
TODAY = date(2025, 5, 25)

# ── output ────────────────────────────────────────────────────────────────────
OUTPUT_PATH = _ROOT / "data" / "internal" / "raw_pos" / "yomyom" / "sample_yomyom_pos.csv"

CSV_COLUMNS = [
    "barcode",
    "product_name",
    "category",
    "brand",
    "supplier",
    "selling_price",
    "cost_price",
    "current_stock",
    "units_sold_7d",
    "units_sold_30d",
    "sales_amount_30d",
    "gross_profit_30d",
    "margin_pct",
    "last_sale_date",
    "last_purchase_date",
]


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT CATALOG
# Each tuple:
#   (barcode_str_or_None, product_name, category, brand, supplier_or_None,
#    selling_price, cost_price, profile)
#
# profile options:
#   fast_essential  – high turnover, thin margin (milk, water, bread)
#   fast_impulse    – high turnover, fat margin (energy drinks, gum, candy)
#   moderate        – average velocity and margin
#   slow_specialty  – niche / premium, low sales, often overstocked
#   dead_stock      – barely moving, high shelf quantity
#
# Barcodes that are explicitly None → will definitely be blank in the CSV.
# Barcodes that have a value → *may* be randomly blanked (~8 % extra).
# Suppliers follow the same logic (~13 % random drop).
# ─────────────────────────────────────────────────────────────────────────────

CATALOG: list[tuple] = [

    # ── Energy Drinks ─────────────────────────────────────────────────────────
    ("7290001010001", "Red Bull Energy Drink 250ml",         "energy_drinks",  "Red Bull",      "Diplomat Distribution",    8.90,  5.20, "fast_impulse"),
    ("7290001010002", "Monster Energy Original 500ml",       "energy_drinks",  "Monster",       "Diplomat Distribution",   11.90,  6.80, "fast_impulse"),
    ("7290001010003", "Burn Energy Drink 500ml",             "energy_drinks",  "Burn",          "Diplomat Distribution",   10.90,  6.20, "moderate"),
    ("7290001010004", "Tiger Energy Drink 250ml",            "energy_drinks",  "Tiger",         "Sakal",                    7.90,  4.30, "moderate"),
    ("7290001010005", "Hell Energy Classic 250ml",           "energy_drinks",  "Hell",          "Sakal",                    7.90,  4.10, "moderate"),
    ("7290001010006", "Rockstar Original 500ml",             "energy_drinks",  "Rockstar",      "Diplomat Distribution",   11.90,  6.90, "slow_specialty"),
    ("7290001010007", "Power Horse Energy 250ml",            "energy_drinks",  "Power Horse",   "Sakal",                    7.50,  4.00, "slow_specialty"),
    ("7290001010008", "XL Energy Drink 500ml",               "energy_drinks",  "XL",            None,                       9.90,  5.50, "moderate"),

    # ── Soft Drinks ───────────────────────────────────────────────────────────
    ("7290001020001", "Coca-Cola 330ml Can",                 "soft_drinks",    "Coca-Cola",     "Coca-Cola Israel",         5.90,  2.90, "fast_impulse"),
    ("7290001020002", "Coca-Cola 1.5L",                      "soft_drinks",    "Coca-Cola",     "Coca-Cola Israel",         8.90,  4.80, "fast_essential"),
    ("7290001020003", "Coca-Cola 500ml Bottle",              "soft_drinks",    "Coca-Cola",     "Coca-Cola Israel",         6.90,  3.50, "fast_impulse"),
    ("7290001020004", "Coca-Cola Zero 330ml Can",            "soft_drinks",    "Coca-Cola",     "Coca-Cola Israel",         5.90,  2.90, "fast_impulse"),
    ("7290001020005", "Pepsi Cola 330ml Can",                "soft_drinks",    "Pepsi",         "Strauss-Elite",            5.90,  2.80, "fast_impulse"),
    ("7290001020006", "Pepsi Cola 1.5L",                     "soft_drinks",    "Pepsi",         "Strauss-Elite",            8.50,  4.50, "moderate"),
    ("7290001020007", "Fanta Orange 330ml Can",              "soft_drinks",    "Fanta",         "Coca-Cola Israel",         5.90,  2.80, "fast_impulse"),
    ("7290001020008", "Sprite 330ml Can",                    "soft_drinks",    "Sprite",        "Coca-Cola Israel",         5.90,  2.80, "fast_impulse"),
    ("7290001020009", "7UP 330ml Can",                       "soft_drinks",    "7UP",           "Strauss-Elite",            5.90,  2.80, "moderate"),
    ("7290001020010", "Schweppes Soda Water 1.5L",           "soft_drinks",    "Schweppes",     "Coca-Cola Israel",         7.90,  4.20, "moderate"),
    ("7290001020011", "Mirinda Orange 330ml Can",            "soft_drinks",    "Mirinda",       "Strauss-Elite",            5.50,  2.70, "slow_specialty"),
    ("7290001020012", "Canada Dry Ginger Ale 330ml",         "soft_drinks",    "Canada Dry",    "Coca-Cola Israel",         5.90,  3.10, "slow_specialty"),
    ("7290001020013", "Mountain Dew 500ml",                  "soft_drinks",    "Mountain Dew",  "Strauss-Elite",            7.90,  4.30, "moderate"),

    # ── Water ─────────────────────────────────────────────────────────────────
    ("7290001030001", "Neviot Mineral Water 0.5L",           "water",          "Neviot",        "Tempo Beverages",          3.90,  2.00, "fast_essential"),
    ("7290001030002", "Neviot Mineral Water 1.5L",           "water",          "Neviot",        "Tempo Beverages",          5.90,  3.10, "fast_essential"),
    ("7290001030003", "Mei Eden Natural Water 0.5L",         "water",          "Mei Eden",      "Eden Springs",             4.20,  2.20, "fast_essential"),
    ("7290001030004", "Mei Eden Natural Water 1.5L",         "water",          "Mei Eden",      "Eden Springs",             6.20,  3.30, "fast_essential"),
    (None,            "Soda Water Generic 1.5L",             "water",          "Generic",       None,                       4.90,  2.80, "moderate"),
    ("7290001030006", "Gan Shmuel Mineral Water 1.5L",       "water",          "Gan Shmuel",    "Gan Shmuel Foods",         5.50,  2.90, "moderate"),

    # ── Snacks ────────────────────────────────────────────────────────────────
    ("7290001040001", "Bamba Peanut Snack 80g",              "snacks",         "Osem",          "Osem Nestlé",              5.90,  3.20, "fast_impulse"),
    ("7290001040002", "Bisli BBQ 70g",                       "snacks",         "Osem",          "Osem Nestlé",              5.90,  3.10, "fast_impulse"),
    ("7290001040003", "Bisli Falafel 70g",                   "snacks",         "Osem",          "Osem Nestlé",              5.90,  3.10, "moderate"),
    ("7290001040004", "Doritos Nacho Cheese 75g",            "snacks",         "Doritos",       "Strauss-Elite",            8.90,  5.20, "fast_impulse"),
    ("7290001040005", "Lay's Classic Salted 75g",            "snacks",         "Lay's",         "Strauss-Elite",            8.90,  5.20, "fast_impulse"),
    ("7290001040006", "Pringles Original 165g",              "snacks",         "Pringles",      "Diplomat Distribution",   14.90,  8.50, "moderate"),
    ("7290001040007", "Tapuchips Ketchup 75g",               "snacks",         "Osem",          "Osem Nestlé",              7.90,  4.40, "fast_impulse"),
    ("7290001040008", "Pretzel Sticks Salted 150g",          "snacks",         "Osem",          "Osem Nestlé",              6.90,  3.80, "moderate"),
    ("7290001040009", "Kayla Sunflower Seeds 100g",          "snacks",         "Kayla",         "Kayla",                    5.90,  3.00, "moderate"),
    ("7290001040010", "Pumpkin Seeds Salted 100g",           "snacks",         "Kayla",         "Kayla",                    6.90,  3.50, "slow_specialty"),
    ("7290001040011", "Mixed Nuts Premium 150g",             "snacks",         "Kayla",         "Kayla",                   14.90,  8.00, "slow_specialty"),
    ("7290001040012", "Corn Chips Chili 100g",               "snacks",         "Osem",          "Osem Nestlé",              8.90,  5.00, "moderate"),
    (None,            "Sesame Snaps 40g",                    "snacks",         "Carmit",        "Carmit Candy",             4.90,  2.60, "slow_specialty"),
    ("7290001040014", "Popcorn Butter Flavour 80g",          "snacks",         "Amiran",        None,                       6.90,  3.80, "moderate"),
    ("7290001040015", "Chocolate Wafers 100g",               "snacks",         "Osem",          "Osem Nestlé",              7.90,  4.20, "moderate"),
    ("7290001040016", "Krembo Marshmallow Chocolate 33g",    "snacks",         "Strauss",       "Strauss-Elite",            4.90,  2.50, "fast_impulse"),
    ("7290001040017", "Rugelach Chocolate Filled 100g",      "snacks",         "Osem",          "Osem Nestlé",              8.90,  5.00, "moderate"),
    ("7290001040018", "Potato Chips Jalapeño 80g",           "snacks",         "Lay's",         "Strauss-Elite",            9.90,  5.80, "slow_specialty"),

    # ── Chocolate ────────────────────────────────────────────────────────────
    ("7290001050001", "Kinder Bueno Milk Chocolate 43g",     "chocolate",      "Kinder",        "Diplomat Distribution",    8.90,  5.50, "fast_impulse"),
    ("7290001050002", "Kinder Bueno White 43g",              "chocolate",      "Kinder",        "Diplomat Distribution",    8.90,  5.50, "moderate"),
    ("7290001050003", "Milka Oreo Chocolate 100g",           "chocolate",      "Milka",         "Diplomat Distribution",   11.90,  7.20, "moderate"),
    ("7290001050004", "Lion Bar 42g",                        "chocolate",      "Nestlé",        "Osem Nestlé",              8.90,  5.30, "moderate"),
    ("7290001050005", "KitKat 4-Finger 41.5g",              "chocolate",      "Nestlé",        "Osem Nestlé",              7.90,  4.80, "fast_impulse"),
    ("7290001050006", "Snickers 50g",                        "chocolate",      "Mars",          "Diplomat Distribution",    9.90,  5.90, "fast_impulse"),
    ("7290001050007", "Twix Twin Bar 50g",                   "chocolate",      "Mars",          "Diplomat Distribution",    9.90,  5.90, "moderate"),
    ("7290001050008", "Bounty Coconut Bar 57g",              "chocolate",      "Mars",          "Diplomat Distribution",    9.90,  5.80, "slow_specialty"),
    ("7290001050009", "Mars Bar 51g",                        "chocolate",      "Mars",          "Diplomat Distribution",    9.90,  5.90, "slow_specialty"),
    ("7290001050010", "Elite Milk Chocolate 100g",           "chocolate",      "Elite",         "Strauss-Elite",           11.90,  7.10, "moderate"),
    ("7290001050011", "Elite Dark Chocolate 70% 100g",       "chocolate",      "Elite",         "Strauss-Elite",           13.90,  8.50, "slow_specialty"),
    ("7290001050012", "Pesek Zman Chocolate Bar 50g",        "chocolate",      "Strauss",       "Strauss-Elite",            7.90,  4.60, "moderate"),
    (None,            "Ferrero Rocher 3-Pack 37.5g",         "chocolate",      "Ferrero",       "Diplomat Distribution",   14.90,  9.80, "slow_specialty"),
    ("7290001050014", "After Eight Mint Chocolate 200g",     "chocolate",      "Nestlé",        "Osem Nestlé",             24.90, 15.50, "dead_stock"),

    # ── Dairy ─────────────────────────────────────────────────────────────────
    ("7290001060001", "Tnuva Full-Fat Milk 3% 1L",           "dairy",          "Tnuva",         "Tnuva",                    6.90,  5.10, "fast_essential"),
    ("7290001060002", "Tnuva Reduced-Fat Milk 1.5% 1L",      "dairy",          "Tnuva",         "Tnuva",                    6.90,  5.00, "fast_essential"),
    ("7290001060003", "Tnuva Cottage Cheese 5% 250g",        "dairy",          "Tnuva",         "Tnuva",                    8.90,  5.90, "fast_essential"),
    ("7290001060004", "Yoplait Vanilla Yogurt 150g",         "dairy",          "Yoplait",       "Strauss-Elite",            5.90,  3.60, "moderate"),
    ("7290001060005", "Danone Strawberry Yogurt 125g",       "dairy",          "Danone",        "Danone Israel",            5.90,  3.50, "moderate"),
    ("7290001060006", "Tnuva Unsalted Butter 100g",          "dairy",          "Tnuva",         "Tnuva",                    7.90,  5.20, "moderate"),
    ("7290001060007", "Strauss Cream Cheese 200g",           "dairy",          "Strauss",       "Strauss-Elite",           11.90,  7.60, "moderate"),
    ("7290001060008", "Tnuva Yellow Hard Cheese 200g",       "dairy",          "Tnuva",         "Tnuva",                   16.90, 11.50, "moderate"),
    ("7290001060009", "Strauss Milky Pudding Chocolate 170g","dairy",          "Strauss",       "Strauss-Elite",            5.90,  3.80, "moderate"),
    ("7290001060010", "Yotvata Chocolate Milk 500ml",        "dairy",          "Yotvata",       "Tnuva",                    8.90,  5.60, "fast_impulse"),
    ("7290001060011", "Tnuva Labaneh Soft Cheese 500g",      "dairy",          "Tnuva",         "Tnuva",                   14.90,  9.80, "moderate"),
    ("7290001060012", "Cornetto Vanilla Ice Cream 120ml",    "dairy",          "Algida",        "Strauss-Elite",            9.90,  5.80, "fast_impulse"),

    # ── Coffee & Tea ──────────────────────────────────────────────────────────
    ("7290001070001", "Elite Gold Instant Coffee 200g",      "coffee_tea",     "Elite",         "Strauss-Elite",           28.90, 17.50, "moderate"),
    ("7290001070002", "Elite Classic Instant Coffee 200g",   "coffee_tea",     "Elite",         "Strauss-Elite",           24.90, 14.90, "moderate"),
    ("7290001070003", "Nescafe Classic Instant Coffee 200g", "coffee_tea",     "Nescafe",       "Osem Nestlé",             27.90, 17.00, "moderate"),
    ("7290001070004", "Nescafe Gold Blend 200g",             "coffee_tea",     "Nescafe",       "Osem Nestlé",             34.90, 21.00, "slow_specialty"),
    ("7290001070005", "Jacobs Kronung Ground Coffee 250g",   "coffee_tea",     "Jacobs",        "Diplomat Distribution",   28.90, 17.50, "slow_specialty"),
    ("7290001070006", "Wissotzky Green Tea 25 bags",         "coffee_tea",     "Wissotzky",     "Wissotzky Tea",           16.90, 10.20, "moderate"),
    ("7290001070007", "Lipton Yellow Label Tea 25 bags",     "coffee_tea",     "Lipton",        "Strauss-Elite",           14.90,  8.80, "moderate"),
    (None,            "Afternoon Earl Grey Tea 20 bags",     "coffee_tea",     "Afternoon",     None,                      18.90, 11.50, "dead_stock"),

    # ── Bakery ────────────────────────────────────────────────────────────────
    ("7290001080001", "Russ Sliced White Bread 750g",        "bakery",         "Russ",          "Russ Bakers",             10.90,  7.20, "fast_essential"),
    ("7290001080002", "Berman Sliced Toast Bread 750g",      "bakery",         "Berman",        "Berman Bakers",           11.90,  7.90, "fast_essential"),
    ("7290001080003", "Whole Wheat Sliced Bread 600g",       "bakery",         "Berman",        "Berman Bakers",           12.90,  8.50, "moderate"),
    ("7290001080004", "Pita Bread 5-Pack 800g",              "bakery",         "Local Bakery",  "Local Supplier",           8.90,  5.50, "fast_essential"),
    ("7290001080005", "Challah Bread 500g",                  "bakery",         "Local Bakery",  "Local Supplier",          12.90,  7.80, "moderate"),
    ("7290001080006", "Sesame Lavash Flatbread 300g",        "bakery",         "Local Bakery",  "Local Supplier",           8.90,  5.20, "moderate"),
    ("7290001080007", "Ka'ak Anise Cookies 400g",            "bakery",         "Local Bakery",  "Local Supplier",          12.90,  7.50, "moderate"),
    ("7290001080008", "Butter Croissant 100g",               "bakery",         "Alon",          None,                       7.90,  4.50, "fast_impulse"),

    # ── Household Basics ──────────────────────────────────────────────────────
    ("7290001090001", "Fairy Dish Soap Lemon 500ml",         "household",      "Fairy",         "Procter & Gamble Israel", 16.90, 10.20, "moderate"),
    ("7290001090002", "Sano Bleach 1L",                      "household",      "Sano",          "Sano",                    10.90,  6.50, "moderate"),
    ("7290001090003", "Sano Toilet Cleaner Gel 750ml",       "household",      "Sano",          "Sano",                    12.90,  7.80, "slow_specialty"),
    ("7290001090004", "Elite Garbage Bags 30L 30-Pack",      "household",      "Elite",         "Strauss-Elite",           18.90, 11.50, "moderate"),
    ("7290001090005", "Hogla Toilet Paper 4-Roll",           "household",      "Hogla",         "Hogla Kimberly",          12.90,  7.90, "fast_essential"),
    ("7290001090006", "Hogla Paper Towels 3-Roll",           "household",      "Hogla",         "Hogla Kimberly",          14.90,  9.20, "moderate"),
    ("7290001090007", "Crystal White Sugar 1kg",             "household",      "Crystal",       "Sugar Industry",           8.90,  5.80, "fast_essential"),
    ("7290001090008", "Fine Table Salt 1kg",                 "household",      "Generic",       None,                       4.90,  2.80, "fast_essential"),
    ("7290001090009", "Paz Sunflower Oil 1L",                "household",      "Paz",           "Paz Oils",                14.90, 11.20, "moderate"),
    ("7290001090010", "Yad Mordechai Extra Virgin Olive Oil 750ml","household","Yad Mordechai", "Yad Mordechai",           34.90, 25.00, "slow_specialty"),

    # ── Ready to Eat ──────────────────────────────────────────────────────────
    ("7290001100001", "Osem Instant Noodles Chicken 85g",    "ready_to_eat",   "Osem",          "Osem Nestlé",              4.90,  2.60, "fast_impulse"),
    ("7290001100002", "Telma Instant Soup Mushroom 3-Pack",  "ready_to_eat",   "Telma",         "Strauss-Elite",            8.90,  5.20, "moderate"),
    ("7290001100003", "Starkist Tuna in Oil 160g",           "ready_to_eat",   "Starkist",      "Diplomat Distribution",   12.90,  7.80, "moderate"),
    ("7290001100004", "Del Monte Corn Kernels 340g",         "ready_to_eat",   "Del Monte",     "Diplomat Distribution",    9.90,  6.20, "slow_specialty"),
    ("7290001100005", "Sabra Hummus Ready-to-Eat 400g",      "ready_to_eat",   "Sabra",         "Sabra",                   14.90,  9.50, "moderate"),
    ("7290001100006", "Al-Arz Tahini Premium 500g",          "ready_to_eat",   "Al-Arz",        "Al-Arz",                  18.90, 12.80, "moderate"),
    ("7290001100007", "Za'atar Spice Mix 100g",              "ready_to_eat",   "Local Brand",   "Local Supplier",           9.90,  5.60, "slow_specialty"),
    (None,            "Sardines in Tomato Sauce 125g",       "ready_to_eat",   "Generic",       None,                       8.90,  5.50, "dead_stock"),

    # ── Juice ─────────────────────────────────────────────────────────────────
    ("7290001110001", "Primor Orange Juice 1L",              "juice",          "Primor",        "Tempo Beverages",         10.90,  6.80, "moderate"),
    ("7290001110002", "Tapuzina Orange Nectar 1L",           "juice",          "Tapuzina",      "Tempo Beverages",          9.90,  6.00, "moderate"),
    ("7290001110003", "Yad Mordechai Pomegranate Juice 1L",  "juice",          "Yad Mordechai", "Yad Mordechai",           18.90, 13.20, "slow_specialty"),
    ("7290001110004", "Cappy Orange Juice 330ml Can",        "juice",          "Cappy",         "Coca-Cola Israel",         6.90,  3.80, "moderate"),
    ("7290001110005", "Jaffa Citrus Juice 1.5L",             "juice",          "Jaffa",         "Tempo Beverages",         12.90,  7.80, "moderate"),
    ("7290001110006", "Minute Maid Apple Juice 330ml",       "juice",          "Minute Maid",   "Coca-Cola Israel",         6.90,  3.90, "slow_specialty"),

    # ── Candy & Gum ───────────────────────────────────────────────────────────
    ("7290001120001", "Extra Spearmint Gum 10-stick",        "candy_gum",      "Wrigley",       "Diplomat Distribution",    3.90,  2.10, "fast_impulse"),
    ("7290001120002", "Orbit Peppermint Gum 14-stick",       "candy_gum",      "Orbit",         "Diplomat Distribution",    4.90,  2.60, "fast_impulse"),
    ("7290001120003", "Haribo Gold Bears 100g",              "candy_gum",      "Haribo",        "Diplomat Distribution",   12.90,  7.80, "moderate"),
    ("7290001120004", "Mentos Fruit Roll 38g",               "candy_gum",      "Mentos",        "Diplomat Distribution",    5.90,  3.20, "fast_impulse"),
    ("7290001120005", "Halls Mentho-Lyptus 9-Pack",         "candy_gum",      "Halls",         "Diplomat Distribution",    5.90,  3.30, "moderate"),
    ("7290001120006", "Skittles Original 45g",               "candy_gum",      "Skittles",      "Diplomat Distribution",    8.90,  5.20, "moderate"),
]

# ─────────────────────────────────────────────────────────────────────────────
# INTENTIONAL DUPLICATE ROWS
# These simulate common POS data-entry errors: same product_name re-keyed
# with a slightly different barcode or price.  Added verbatim to the catalog.
# ─────────────────────────────────────────────────────────────────────────────

DUPLICATES: list[tuple] = [
    # Duplicate 1: Coca-Cola 330ml Can — second entry with different barcode
    ("7290001020099", "Coca-Cola 330ml Can",                 "soft_drinks",    "Coca-Cola",     "Coca-Cola Israel",         5.90,  2.90, "fast_impulse"),

    # Duplicate 2: Bamba Peanut Snack 80g — re-entered with slight price diff
    ("7290001040099", "Bamba Peanut Snack 80g",              "snacks",         "Osem",          "Osem Nestlé",              6.20,  3.20, "fast_impulse"),

    # Duplicate 3: Tnuva Full-Fat Milk 3% 1L — supplier missing this time
    ("7290001060099", "Tnuva Full-Fat Milk 3% 1L",           "dairy",          "Tnuva",         None,                       6.90,  5.10, "fast_essential"),

    # Duplicate 4: Nescafe Classic — same barcode re-entered by mistake
    ("7290001070003", "Nescafe Classic Instant Coffee 200g", "coffee_tea",     "Nescafe",       "Osem Nestlé",             27.90, 17.00, "moderate"),
]


# ─────────────────────────────────────────────────────────────────────────────
# PROFILE → STOCK / SALES PARAMETERS
# ─────────────────────────────────────────────────────────────────────────────

PROFILES: dict[str, dict] = {
    "fast_essential": {
        # High-frequency necessities; often low on shelf before restock
        "stock":              (4, 22),
        "sold_30d":           (65, 200),
        "sold_7d_frac":       (0.23, 0.29),
        "last_sale_days_ago": (0, 2),
        "last_buy_days_ago":  (1, 8),
    },
    "fast_impulse": {
        # Impulse buys near the till; high margin, frequent purchase
        "stock":              (8, 38),
        "sold_30d":           (35, 110),
        "sold_7d_frac":       (0.22, 0.28),
        "last_sale_days_ago": (0, 3),
        "last_buy_days_ago":  (4, 14),
    },
    "moderate": {
        # Standard shelf items; healthy if managed
        "stock":              (14, 52),
        "sold_30d":           (14, 60),
        "sold_7d_frac":       (0.20, 0.27),
        "last_sale_days_ago": (1, 7),
        "last_buy_days_ago":  (7, 25),
    },
    "slow_specialty": {
        # Niche or premium; buyers exist but not daily
        "stock":              (18, 65),
        "sold_30d":           (4, 18),
        "sold_7d_frac":       (0.15, 0.25),
        "last_sale_days_ago": (2, 14),
        "last_buy_days_ago":  (14, 45),
    },
    "dead_stock": {
        # Overordered or wrong product; clogs shelf space
        "stock":              (35, 110),
        "sold_30d":           (0, 5),
        "sold_7d_frac":       (0.0, 0.20),
        "last_sale_days_ago": (8, 30),
        "last_buy_days_ago":  (30, 90),
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _days_ago(n: int) -> str:
    return (TODAY - timedelta(days=n)).isoformat()


def _generate_row(entry: tuple) -> dict:
    """Convert one catalog tuple into a fully populated row dict."""
    barcode_raw, name, category, brand, supplier_raw, sell, cost, profile = entry
    p = PROFILES[profile]

    # ── stock / sales ──────────────────────────────────────────────────────
    sold_30d = _RNG.randint(*p["sold_30d"])
    frac_lo, frac_hi = p["sold_7d_frac"]
    sold_7d  = max(0, round(sold_30d * _RNG.uniform(frac_lo, frac_hi)))
    stock    = _RNG.randint(*p["stock"])

    # ── financials ─────────────────────────────────────────────────────────
    sales_amount_30d  = round(sell * sold_30d, 2)
    gross_profit_30d  = round((sell - cost) * sold_30d, 2)
    margin_pct        = round((sell - cost) / sell * 100, 2)

    # ── dates ──────────────────────────────────────────────────────────────
    last_sale_date     = _days_ago(_RNG.randint(*p["last_sale_days_ago"]))
    last_purchase_date = _days_ago(_RNG.randint(*p["last_buy_days_ago"]))

    return {
        "barcode":            barcode_raw,           # may be None
        "product_name":       name,
        "category":           category,
        "brand":              brand,
        "supplier":           supplier_raw,          # may be None
        "selling_price":      f"{sell:.2f}",
        "cost_price":         f"{cost:.2f}",
        "current_stock":      stock,
        "units_sold_7d":      sold_7d,
        "units_sold_30d":     sold_30d,
        "sales_amount_30d":   f"{sales_amount_30d:.2f}",
        "gross_profit_30d":   f"{gross_profit_30d:.2f}",
        "margin_pct":         f"{margin_pct:.2f}",
        "last_sale_date":     last_sale_date,
        "last_purchase_date": last_purchase_date,
    }


def _apply_random_missing(rows: list[dict]) -> list[dict]:
    """
    Randomly blank out barcode / supplier on an additional ~8 % / ~13 % of
    rows that were not already None.  This is in addition to the explicit
    Nones in the catalog.
    """
    for row in rows:
        if row["barcode"] is not None and _RNG.random() < 0.08:
            row["barcode"] = None
        if row["supplier"] is not None and _RNG.random() < 0.13:
            row["supplier"] = None
    return rows


def _to_csv_value(v) -> str:
    """None → empty string; everything else → str."""
    if v is None:
        return ""
    return str(v)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def generate() -> None:
    logger.info("Building product rows from catalog ({} base + {} duplicates)…",
                len(CATALOG), len(DUPLICATES))

    all_entries = CATALOG + DUPLICATES
    rows = [_generate_row(e) for e in all_entries]
    rows = _apply_random_missing(rows)

    # ── shuffle so duplicates are not obviously at the end ─────────────────
    _RNG.shuffle(rows)

    # ── write CSV ──────────────────────────────────────────────────────────
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: _to_csv_value(row[col]) for col in CSV_COLUMNS})

    # ── stats ──────────────────────────────────────────────────────────────
    total          = len(rows)
    missing_bc     = sum(1 for r in rows if not r["barcode"])
    missing_sup    = sum(1 for r in rows if not r["supplier"])
    dup_names      = len(rows) - len({r["product_name"] for r in rows})
    low_stock_fast = sum(
        1 for r in rows
        if int(r["current_stock"]) < 10 and int(r["units_sold_30d"]) > 40
    )
    dead           = sum(1 for r in rows if int(r["units_sold_30d"]) < 6)

    logger.success("CSV written → {}", OUTPUT_PATH)
    logger.info("  Total rows        : {}", total)
    logger.info("  Missing barcode   : {} ({:.0f}%)", missing_bc,  missing_bc  / total * 100)
    logger.info("  Missing supplier  : {} ({:.0f}%)", missing_sup, missing_sup / total * 100)
    logger.info("  Duplicate names   : {} extra rows", dup_names)
    logger.info("  Low-stock/fast    : {} products need reorder", low_stock_fast)
    logger.info("  Dead-stock rows   : {} products barely selling", dead)


if __name__ == "__main__":
    generate()
