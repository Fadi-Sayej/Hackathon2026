#!/usr/bin/env python3
"""
print_figures.py — recompute every number quoted in intent.md, from the data, now.

WHY THIS EXISTS
    intent.md quotes figures to the shekel and carries them into a meeting with the
    store owner. Those figures go stale on their own: .github/workflows/collect-daily.yml
    scrapes competitor prices every day and regenerates public/data/operational.json, so
    a number written down on Saturday is wrong by Tuesday. A number nobody can reproduce
    in the room is worse than no number — the owner asks "where did that come from?" and
    the answer is a document.

    So the document stops asserting figures and starts citing this script. Run it before
    any meeting; run it in front of the owner if he doubts a line.

WHAT IT REFUSES TO DO
    It prints what the data supports and says "no data" otherwise. It never falls back
    to a remembered constant — a stale figure that looks fresh is the exact failure this
    script exists to prevent.

Usage:
    python3 scripts/print_figures.py            # or: npm run figures
    python3 scripts/print_figures.py --json     # machine-readable
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DASHBOARD = os.path.join(ROOT, "public", "data", "operational.json")
INVENTORY = os.path.join(ROOT, "yomyom-inventory.csv")
SALES_GLOB = os.path.join(ROOT, "data", "internal", "raw_pos", "yomyom", "sales", "*.csv")

# A shelf price this low is a free staff coffee, not a sale; a cost above twice the
# price is a carton cost typed against a unit price. Both are data-entry artefacts,
# and counting them as loss would put a brownie "losing ₪234 a unit" at the top of
# the owner's screen. Mirrors the gate stated in intent.md §7.
MIN_REAL_PRICE = 0.50
MAX_COST_MULTIPLE = 2.0


def _num(value, default=None):
    """Parse a POS numeric cell. Returns default rather than raising."""
    if value is None:
        return default
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return default


def _is_data_entry_error(selling, cost):
    """True when the price/cost pair cannot describe a real sale."""
    if selling is None or selling < MIN_REAL_PRICE:
        return True
    if cost is not None and cost > selling * MAX_COST_MULTIPLE:
        return True
    return False


def load_dashboard():
    if not os.path.exists(DASHBOARD):
        return None
    with open(DASHBOARD, encoding="utf-8") as fh:
        return json.load(fh)


# The owner's own Wolt markup policy, read off his data rather than assumed. The
# density of markups collapses from 81 items in the 16-18% band to 8 in 18-20% — a
# 90% cliff — so 18% is where his deliberate policy stops and something else starts.
# A flat "30% is the Wolt commission" assumption would have flagged 1,147 items as
# losses when 79% of his catalogue is priced identically on both channels.
WOLT_POLICY_CEILING_PCT = 18.0

# Against competitors the same elbow analysis puts the statistical break at 90%
# (34 items -> 6). But 90% is too permissive to act on, so a commercial threshold
# sits at 60% — three times the natural forecourt-vs-supermarket gap of ~20%.
MARKET_ANOMALY_PCT = 90.0
MARKET_REVIEW_PCT = 60.0


def wolt_policy_figures():
    """Intent 1 — his shelf price against his own Wolt price, split by his policy."""
    if not os.path.exists(INVENTORY):
        return None
    with open(INVENTORY, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    keys = {k.strip(): k for k in rows[0].keys()}

    same, cheaper, within, above = 0, [], 0, []
    for row in rows:
        shelf = _num(row.get(keys["מחיר מכירה"]))
        wolt = _num(row.get(keys["WOLT"]))
        if not shelf or not wolt or shelf <= 0:
            continue
        if abs(wolt - shelf) < 0.005:
            same += 1
        elif wolt < shelf:
            cheaper.append((shelf - wolt, (row.get(keys["תאור פריט"]) or "").strip()))
        else:
            pct = (wolt / shelf - 1) * 100
            if pct > WOLT_POLICY_CEILING_PCT:
                above.append((pct, (row.get(keys["תאור פריט"]) or "").strip()))
            else:
                within += 1

    cheaper.sort(reverse=True)
    above.sort(reverse=True)
    return {
        "priced_both": same + len(cheaper) + within + len(above),
        "identical": same,
        "cheaper_on_wolt": len(cheaper),
        "cheaper_worst": cheaper[0] if cheaper else None,
        "within_policy": within,
        "above_policy": len(above),
        "above_worst": above[0] if above else None,
    }


def per_sale_figures(rows):
    """Intent 1 (legacy view) — the raw per-sale sums, kept for continuity."""
    wolt = [r for r in rows if r.get("type") == "CHECK_WOLT_PRICE_GAP"]
    margin = [r for r in rows if r.get("type") == "CHECK_MARGIN"]

    wolt_kept, wolt_gap = [], 0.0
    for r in wolt:
        sell, wp = r.get("sellingPrice"), r.get("woltPrice")
        if sell is None or wp is None or _is_data_entry_error(sell, None):
            continue
        wolt_kept.append(r)
        wolt_gap += wp - sell

    margin_kept, margin_loss = [], 0.0
    for r in margin:
        sell, cost = r.get("sellingPrice"), r.get("costPrice")
        if sell is None or cost is None or _is_data_entry_error(sell, cost):
            continue
        margin_kept.append(r)
        margin_loss += cost - sell

    return {
        "wolt_flagged": len(wolt),
        "wolt_counted": len(wolt_kept),
        "wolt_gap": round(wolt_gap, 2),
        "margin_flagged": len(margin),
        "margin_counted": len(margin_kept),
        "margin_loss": round(margin_loss, 2),
        "per_sale_total": round(wolt_gap + margin_loss, 2),
    }


def stock_discrepancy_figures(rows):
    """Intent 2 — split by whether the stock number underneath is believable."""
    disc = [r for r in rows if r.get("type") == "CHECK_STOCK_DISCREPANCY"]

    def value(subset):
        return round(
            sum((r.get("metricValue") or 0) * (r.get("costPrice") or 0) for r in subset), 2
        )

    solid = [r for r in disc if (r.get("currentStock") or 0) >= 0]
    estimated = [r for r in disc if (r.get("currentStock") or 0) < 0]

    return {
        "total_items": len(disc),
        "solid_items": len(solid),
        "solid_value": value(solid),
        "estimated_items": len(estimated),
        "estimated_value": value(estimated),
        "combined_value": value(disc),
    }


def hygiene_figures(rows):
    """Intent 2b — real work, deliberately carrying no shekel figure."""
    counts = Counter(r.get("type") for r in rows)
    return {
        "negative_stock": counts.get("CHECK_NEGATIVE_STOCK", 0),
        "unknown_barcode": counts.get("VERIFY_UNKNOWN_BARCODE", 0),
    }


def catalogue_figures():
    """Intent 9 — how much of the catalogue is alive, measured against real sales."""
    sales_files = sorted(glob.glob(SALES_GLOB))
    if not sales_files or not os.path.exists(INVENTORY):
        return None

    sold, revenue, rows_read = Counter(), 0.0, 0
    for path in sales_files:
        with open(path, encoding="utf-8-sig") as fh:
            for raw in csv.DictReader(fh):
                row = {k.strip(): (v or "").strip() for k, v in raw.items() if k}
                barcode = row.get("ברקוד/קוד", "")
                if not barcode:
                    continue
                rows_read += 1
                units = _num(row.get("מכר"), 0.0)
                sold[barcode] += units
                revenue += units * _num(row.get("מחיר מכירה"), 0.0)

    with open(INVENTORY, encoding="utf-8-sig") as fh:
        inventory = list(csv.DictReader(fh))
    keys = {k.strip(): k for k in inventory[0].keys()}

    ghosts, idle, idle_value, with_barcode = 0, 0, 0.0, 0
    top_idle = []
    for row in inventory:
        barcode = (row.get(keys["ברקוד"]) or "").strip()
        if not barcode:
            continue
        with_barcode += 1
        if sold[barcode] > 0:
            continue
        stock = _num(row.get(keys["מלאי נוכחי"]), 0.0)
        cost = _num(row.get(keys["מחיר קניה"]), 0.0)
        if stock == 0:
            ghosts += 1
        elif stock > 0:
            idle += 1
            value = stock * cost
            idle_value += value
            top_idle.append((value, stock, (row.get(keys["תאור פריט"]) or "").strip()))

    top_idle.sort(reverse=True)
    live = sum(1 for b in sold if sold[b] > 0 and b in {
        (r.get(keys["ברקוד"]) or "").strip() for r in inventory
    })

    return {
        "sales_rows": rows_read,
        "sales_barcodes": len(sold),
        "total_units": round(sum(sold.values())),
        "revenue": round(revenue),
        "catalogue_with_barcode": with_barcode,
        "live_items": live,
        "dead_items": with_barcode - live,
        "ghost_items": ghosts,
        "idle_items": idle,
        "idle_value": round(idle_value),
        "largest_idle": top_idle[0] if top_idle else None,
    }


def missing_cost_figures():
    """Intent 10 — how many cost questions actually reach the owner."""
    sales_files = sorted(glob.glob(SALES_GLOB))
    if not sales_files or not os.path.exists(INVENTORY):
        return None

    sold = Counter()
    for path in sales_files:
        with open(path, encoding="utf-8-sig") as fh:
            for raw in csv.DictReader(fh):
                row = {k.strip(): (v or "").strip() for k, v in raw.items() if k}
                barcode = row.get("ברקוד/קוד", "")
                if barcode:
                    sold[barcode] += _num(row.get("מכר"), 0.0)

    with open(INVENTORY, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    keys = {k.strip(): k for k in rows[0].keys()}

    dead_no_stock, dead_with_stock, alive = 0, 0, []
    for row in rows:
        if _num(row.get(keys["מחיר קניה"]), 0.0) > 0:
            continue
        barcode = (row.get(keys["ברקוד"]) or "").strip()
        if barcode and sold[barcode] > 0:
            alive.append((sold[barcode], (row.get(keys["תאור פריט"]) or "").strip()))
        elif _num(row.get(keys["מלאי נוכחי"]), 0.0) > 0:
            dead_with_stock += 1
        else:
            dead_no_stock += 1

    alive.sort(reverse=True)
    return {
        "total": dead_no_stock + dead_with_stock + len(alive),
        "archived_no_question": dead_no_stock,
        "deferred": dead_with_stock,
        "ask_owner": len(alive),
        "top_ask": alive[:3],
    }


def money(value):
    return f"₪{value:,.2f}" if abs(value) < 1000 else f"₪{value:,.0f}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a report")
    args = parser.parse_args()

    dashboard = load_dashboard()
    if dashboard is None:
        print(
            f"public/data/operational.json is missing.\n"
            f"Run `npm run data:refresh` first — this script never guesses.",
            file=sys.stderr,
        )
        return 1

    rows = dashboard.get("recommendations", [])
    generated = dashboard.get("meta", {}).get("generatedAt", "unknown")

    result = {
        "printed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_generated_at": generated,
        "per_sale": per_sale_figures(rows),
        "wolt_policy": wolt_policy_figures(),
        "stock_discrepancy": stock_discrepancy_figures(rows),
        "hygiene": hygiene_figures(rows),
        "catalogue": catalogue_figures(),
        "missing_cost": missing_cost_figures(),
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    ps, sd, hy, cat = (
        result["per_sale"],
        result["stock_discrepancy"],
        result["hygiene"],
        result["catalogue"],
    )
    wp, mc = result["wolt_policy"], result["missing_cost"]

    print()
    print("=" * 68)
    print("  SmartShelf — الأرقام، محسوبة الآن من البيانات")
    print("=" * 68)
    print(f"  البيانات وُلّدت:  {result['data_generated_at']}")
    print(f"  طُبع الآن:       {result['printed_at']}")
    print()

    print("─" * 68)
    print("  النية 1 — ما يكلّفه كل عملية بيع  (متكرّر)")
    print("─" * 68)
    print(f"  فجوات سعر Wolt      {ps['wolt_counted']:>6} صنف   {money(ps['wolt_gap']):>14}")
    print(f"  هوامش خاسرة          {ps['margin_counted']:>6} صنف   {money(ps['margin_loss']):>14}")
    print(f"  {'':>28}{'─' * 16}")
    print(f"  المجموع لكل عملية بيع{'':>13}{money(ps['per_sale_total']):>14}")
    if ps["margin_flagged"] != ps["margin_counted"]:
        skipped = ps["margin_flagged"] - ps["margin_counted"]
        print(f"    (استُبعد {skipped} صنفاً كأخطاء إدخال: سعر < ₪0.50 أو تكلفة > ضعف السعر)")
    print()

    if wp:
        print("─" * 68)
        print(f"  النية 1 — سياسة Wolt الفعلية  (العتبة {WOLT_POLICY_CEILING_PCT:.0f}%، من بياناته)")
        print("─" * 68)
        pct_same = 100 * wp["identical"] / wp["priced_both"]
        print(f"  Wolt = الرف بالضبط   {wp['identical']:>6} صنف   ({pct_same:.0f}%) ← لا يُعرض")
        print(f"  ضمن سياسته (0-18%)   {wp['within_policy']:>6} صنف   ← لا يُعرض")
        print(f"  🔴 Wolt أرخص من الرف {wp['cheaper_on_wolt']:>6} صنف   ← خسارة مؤكدة")
        if wp["cheaper_worst"]:
            gap, name = wp["cheaper_worst"]
            print(f"      أسوأها: {name[:30]} — فرق {money(gap)}")
        print(f"  ⚠ فوق سياسته (>18%)  {wp['above_policy']:>6} صنف   ← مقصود؟")
        if wp["above_worst"]:
            pct, name = wp["above_worst"]
            print(f"      أعلاها: {name[:30]} — +{pct:.0f}%")
        print()

    print("─" * 68)
    print("  النية 2 — مخزون لا تتطابق أرقامه  (مرّة واحدة، لا يتكرّر)")
    print("─" * 68)
    print(f"  حساب متماسك          {sd['solid_items']:>6} صنف   {money(sd['solid_value']):>14}   ← حقيقة")
    print(f"  مخزونه سالب أصلاً    {sd['estimated_items']:>6} صنف   {money(sd['estimated_value']):>14}   ← تقدير")
    print(f"  {'':>28}{'─' * 16}")
    print(f"  المجموع              {sd['total_items']:>6} صنف   {money(sd['combined_value']):>14}")
    print()
    print("  ⚠ لا يُجمع هذا المبلغ مع مبلغ النية 1 — الأول متكرّر والثاني واقف.")
    print()

    print("─" * 68)
    print("  النية 2ب — نظافة بيانات  (بلا مبلغ، عمداً)")
    print("─" * 68)
    print(f"  مخزون سالب           {hy['negative_stock']:>6} صف")
    print(f"  باركود مجهول         {hy['unknown_barcode']:>6} صنف")
    print()

    if cat:
        print("─" * 68)
        print("  النية 9 — كم من الكتالوج حيّ فعلاً")
        print("─" * 68)
        pct_live = 100 * cat["live_items"] / cat["catalogue_with_barcode"]
        print(f"  باع خلال الفترة      {cat['live_items']:>6} صنف   ({pct_live:.0f}% من الكتالوج)")
        print(f"  لم يبع شيئاً          {cat['dead_items']:>6} صنف   ({100 - pct_live:.0f}%)")
        print(f"    منها أشباح (مخزون صفر){cat['ghost_items']:>4} صنف   ← قابلة للأرشفة بلا سؤال")
        print(f"    منها عليها مخزون     {cat['idle_items']:>5} صنف   {money(cat['idle_value']):>14}")
        if cat["largest_idle"]:
            value, stock, name = cat["largest_idle"]
            print(f"      أكبرها: {name[:34]}")
            print(f"      {money(value)} — مخزون {stock:,.0f} وحدة، صفر مبيعات")
        print()
        print(f"  مبيعات الفترة        {cat['total_units']:,} وحدة · {money(cat['revenue'])}")
        print(f"  ({cat['sales_rows']:,} صفاً على {cat['sales_barcodes']:,} باركود)")
        print()
    else:
        print("  النية 9 — ملفات المبيعات غير موجودة، فلا رقم يُطبع.")
        print()

    if mc:
        print("─" * 68)
        print("  النية 10 — أصناف بلا سعر تكلفة، وكم سؤالاً يصل المالك فعلاً")
        print("─" * 68)
        print(f"  بلا تكلفة إجمالاً     {mc['total']:>6} صنف")
        print(f"    تُحذف مع النية 9    {mc['archived_no_question']:>6} صنف   ← بلا سؤال")
        print(f"    سؤال مؤجّل          {mc['deferred']:>6} صنف")
        print(f"  ✅ يُسأل عنها فعلاً    {mc['ask_owner']:>6} صنف   ← دقيقتان من وقته")
        for units, name in mc["top_ask"]:
            print(f"      باع {units:>6,.0f} وحدة — {name[:34]}")
        print()

    print("=" * 68)
    print("  شغّل هذا قبل أي اجتماع. وإن شُكّك في رقم — شغّله أمامه.")
    print("=" * 68)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
