---
ID: IDLE-ANSWERS-2026-09-28
Title: Idle stock's three answers, and how a calculated reference was made — for approval
Status: Approved — by the repository owner: both changes on 2026-09-28 ("yes to all"), the wording and screenshots on 2026-09-29 ("approved"); merged as #243
Owner: smartshelf-engineer
Parent: [F4-S1](../features/F4-catalogue-lifecycle/specs/F4-S1-catalogue-lifecycle.md), [F3-S1](../features/F3-competitor-price-position/specs/F3-S1-competitor-price-position.md)
Inputs: [docs/reviews/F3-validation.md, docs/reviews/F4-validation.md, public/data/dashboard.json (2026-09-28)]
Updated: 2026-09-28
---

# Idle stock's answers, and the Prices page's reference

## 1. An idle product is answered with what he found (F4 FR-070, AC-071b)

A product with stock that sold nothing in seven months no longer gets the generic Done / Not
worth it. It gets the three answers F4-S1 asks for, and Later stays. Each is recorded apart:

| Answer | English | العربية | עברית | Recorded as |
|---|---|---|---|---|
| On the shelf, not selling | On the shelf, not selling | على الرف، لا يُباع | על המדף, לא נמכר | done, reason `still_stocked` |
| The count is wrong | The count is wrong | العدد خطأ | הספירה שגויה | not worth it, reason `wrong_data` (the data is wrong) |
| We don't sell it anymore | We don't sell it anymore | لم نعد نبيعه | כבר לא מוכרים אותו | done, reason `no_longer_carried` |

The two new reasons join the owner state's list (`ownerState.js`, System Design §10.3). The
same answers appear on the implausible quantity's card, which is also an idle product.

[idle-card-ar.png](idle-answers-2026-09-28/idle-card-ar.png)

## 2. A calculated reference says how it was made (F3 AC-042, AC-053)

Under a reference no shop actually charges, the Prices page now says what it is:

| Reference | English | العربية | עברית |
|---|---|---|---|
| a supermarket price plus the measured allowance | supermarket + {pct} | سوبرماركت + {pct} | סופרמרקט + {pct} |
| the average of a supermarket and a shop like his | average of a supermarket and a shop like yours | متوسط سوبرماركت ومتجر مثل متجرك | ממוצע של סופרמרקט וחנות כמו שלך |

A price from one shop like his carries no note.

[prices-ar.png](idle-answers-2026-09-28/prices-ar.png)
