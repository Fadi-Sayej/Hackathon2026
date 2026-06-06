# Operational Recommendations

- Generated at: 2026-06-06T12:31:21.783789+00:00
- Total recommendations: 2184
- Source rows scanned: products=7674, inventory=7674, margins=7674, expiry_alerts=1

## Summary by type

- CHECK_MARGIN: 104
- CHECK_NEGATIVE_STOCK: 625
- CHECK_WOLT_PRICE_GAP: 1147
- PROMOTE_EXPIRING_PRODUCT: 1
- VERIFY_UNKNOWN_BARCODE: 307

## CHECK_MARGIN (top 10 of 104)

- אבטיח | confidence=0.85 | sell=5.9 cost=10.0 margin=-69.49% | Selling below cost — losing money on every sale.
- אגס | confidence=0.85 | sell=14.9 cost=15.0 margin=-0.67% | Selling below cost — losing money on every sale.
- אננס | confidence=0.85 | sell=25.9 cost=40.0 margin=-54.44% | Selling below cost — losing money on every sale.
- אספרסו רגיל - עובדים | confidence=0.85 | sell=0.01 cost=0.84 margin=-8300.0% | Selling below cost — losing money on every sale.
- אפרסק | confidence=0.85 | sell=9.9 cost=23.0 margin=-132.32% | Selling below cost — losing money on every sale.
- אפרסק | confidence=0.85 | sell=10.0 cost=35.0 margin=-250.0% | Selling below cost — losing money on every sale.
- בונזור מפה חמאה מלטח תפןא וגבינות | confidence=0.85 | sell=164.99 cost=174.77 margin=-5.93% | Selling below cost — losing money on every sale.
- ביצים חופשיות 12 יח | confidence=0.85 | sell=14.24 cost=23.6 margin=-65.73% | Selling below cost — losing money on every sale.
- בלונדי-קרם אגוזי לוז | confidence=0.85 | sell=8.0 cost=8.4 margin=-5.0% | Selling below cost — losing money on every sale.
- בננה מובחרת | confidence=0.85 | sell=8.9 cost=11.0 margin=-23.6% | Selling below cost — losing money on every sale.

## CHECK_NEGATIVE_STOCK (top 10 of 625)

- - Cycle Car 2A 2USBמטען רכב | confidence=0.90 | stock=-3 | POS reports negative on-hand stock — count or fix data before reordering.
- 10 לחמניות אצבע ארוז | confidence=0.90 | stock=-181 | POS reports negative on-hand stock — count or fix data before reordering.
- 10 פיתה ביס כוסמין מלא | confidence=0.90 | stock=-84 | POS reports negative on-hand stock — count or fix data before reordering.
- 10 פיתה קלה ביס | confidence=0.90 | stock=-33 | POS reports negative on-hand stock — count or fix data before reordering.
- 12 ביצים טריות L | confidence=0.90 | stock=-204 | POS reports negative on-hand stock — count or fix data before reordering.
- 12 ביצים טריות M | confidence=0.90 | stock=-23 | POS reports negative on-hand stock — count or fix data before reordering.
- 3 בייגלה רומני ארוז | confidence=0.90 | stock=-9 | POS reports negative on-hand stock — count or fix data before reordering.
- 6 חליות מתוק אגמי | confidence=0.90 | stock=-63 | POS reports negative on-hand stock — count or fix data before reordering.
- 8 לחמניה ביס כוסמין | confidence=0.90 | stock=-1 | POS reports negative on-hand stock — count or fix data before reordering.
- Cube world mag | confidence=0.90 | stock=-3 | POS reports negative on-hand stock — count or fix data before reordering.

## CHECK_WOLT_PRICE_GAP (top 10 of 1147)

- - Cycle Car 2A 2USBמטען רכב | confidence=0.95 | shelf=24.9 wolt=37.9 gap=52.21% | WOLT price is 52% above the shelf price — align or confirm intentional.
- במבה פרו 80 ג'ר | confidence=0.95 | shelf=6.9 wolt=12.8 gap=85.51% | WOLT price is 86% above the shelf price — align or confirm intentional.
- בראוניז שוקולד במגש 40 | confidence=0.95 | shelf=1.9 wolt=2.9 gap=52.63% | WOLT price is 53% above the shelf price — align or confirm intentional.
- דיפלומט מילקה טינס | confidence=0.95 | shelf=15.9 wolt=25.9 gap=62.89% | WOLT price is 63% above the shelf price — align or confirm intentional.
- טחינה 500ג הר ברכה | confidence=0.95 | shelf=17.9 wolt=26.9 gap=50.28% | WOLT price is 50% above the shelf price — align or confirm intentional.
- יפן פאנטה תפוח אדום 50 | confidence=0.95 | shelf=8.9 wolt=12.9 gap=44.94% | WOLT price is 45% above the shelf price — align or confirm intentional.
- לה קט נתחוני טונה 85 גרם | confidence=0.95 | shelf=4.9 wolt=7.9 gap=61.22% | WOLT price is 61% above the shelf price — align or confirm intentional.
- לה קט פטה כבד עוף 85 גרם | confidence=0.95 | shelf=4.9 wolt=7.9 gap=61.22% | WOLT price is 61% above the shelf price — align or confirm intentional.
- מטען רכב mower 48 w | confidence=0.95 | shelf=59.9 wolt=98.0 gap=63.61% | WOLT price is 64% above the shelf price — align or confirm intentional.
- מיני טרופיקש 200 מ״ל | confidence=0.95 | shelf=1.9 wolt=2.9 gap=52.63% | WOLT price is 53% above the shelf price — align or confirm intentional.

## PROMOTE_EXPIRING_PRODUCT (top 1 of 1)

- מוצר בדיקה -1 | confidence=0.90 | expiry=2026-06-10 days=4 stock=0 | Verify stock count before action.

## VERIFY_UNKNOWN_BARCODE (top 10 of 307)

- אבוקדו | confidence=0.55 | Catalog item has no barcode — cannot be matched, scanned, or tracked for expiry.
- אגוזי מלח | confidence=0.55 | Catalog item has no barcode — cannot be matched, scanned, or tracked for expiry.
- אוטוקיר - שטיפה משאית | confidence=0.55 | Catalog item has no barcode — cannot be matched, scanned, or tracked for expiry.
- אוטוקיר - שטיפה פרטי | confidence=0.55 | Catalog item has no barcode — cannot be matched, scanned, or tracked for expiry.
- אייס בראד | confidence=0.55 | Catalog item has no barcode — cannot be matched, scanned, or tracked for expiry.
- אייס בראד עובדים | confidence=0.55 | Catalog item has no barcode — cannot be matched, scanned, or tracked for expiry.
- אייס קפה | confidence=0.55 | Catalog item has no barcode — cannot be matched, scanned, or tracked for expiry.
- אנונה | confidence=0.55 | Catalog item has no barcode — cannot be matched, scanned, or tracked for expiry.
- אספראגוס | confidence=0.55 | Catalog item has no barcode — cannot be matched, scanned, or tracked for expiry.
- אספרסו | confidence=0.55 | Catalog item has no barcode — cannot be matched, scanned, or tracked for expiry.
