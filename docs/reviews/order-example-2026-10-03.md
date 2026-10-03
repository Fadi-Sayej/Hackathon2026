---
ID: D29-ORDER-EXAMPLE-REVIEW
Title: The order pages' example — screens for the repository owner's approval
Status: Ready for review
Owner: smartshelf-engineer
Parent: [D-29](../product/intent-register.md#3-decisions-already-made-by-the-intent-layer)
Inputs: [D-29, docs/reviews/F8-screens-mockups.md, scripts/build_order_example.py, public/examples/order-example.json, src/pages/OrderExample.jsx, src/pages/ReorderPage.jsx, src/pages/ApprovedOrdersPage.jsx]
Updated: 2026-10-03
---

# The order pages' example — screens for approval

D-29 (2026-10-03): while Reorder and Approved orders wait for daily sales reports, each may
show an example of itself, inside a clearly marked preview. Front-end work waits for the
repository owner's approval, so these are the screens, taken from the real built app (the
e2e build) on 2026-10-03.

## What is on them

- **The button:** under Reorder's waiting message, "See how this page looks". Approved orders
  shows it while nothing has been approved.
- **The example:** the real page, filled from a test shop that
  `scripts/build_order_example.py` builds from the order probe's fixture world. Every figure is
  the engine's. The test shop has five departments, so every kind of line appears:
  - a suggestion the market boost raised;
  - bakery orders capped by a two-day shelf life;
  - a count the page could not use;
  - a product its stock already covers;
  - products that do not sell every week;
  - two departments missing a fact.
- **The fence:**
  - an amber dashed frame;
  - a banner: "Example: a test shop, not your data. Nothing here can be approved, saved or sent.";
  - an "Example" tag on every card, table and missing-fact box, because the banner scrolls
    away.
- **Nothing works in it:** every button is disabled (approve, change, dismiss, and the CSV
  download), and nothing pressed is recorded. The engine, the published data, the owner
  state and the pilot measurement never read it. The button disappears once the store has
  suggestions or approvals of its own.

## The screens

| Screen | File |
|---|---|
| Reorder, waiting, with the button (English) | [reorder-waiting-en.png](order-example-2026-10-03/reorder-waiting-en.png) |
| Reorder, example open (English) | [reorder-example-en.png](order-example-2026-10-03/reorder-example-en.png) |
| Reorder, the whole example (English) | [reorder-example-full-en.png](order-example-2026-10-03/reorder-example-full-en.png) |
| Reorder, example open (Hebrew, Arabic) | [he](order-example-2026-10-03/reorder-example-he.png) · [ar](order-example-2026-10-03/reorder-example-ar.png) |
| Reorder on a phone, scrolled into the example (Arabic) | [reorder-example-phone-scrolled-ar.png](order-example-2026-10-03/reorder-example-phone-scrolled-ar.png) |
| Approved orders, example open (English, Hebrew, Arabic) | [en](order-example-2026-10-03/orders-example-en.png) · [he](order-example-2026-10-03/orders-example-he.png) · [ar](order-example-2026-10-03/orders-example-ar.png) |

## The words, in three languages

| | English | עברית | العربية |
|---|---|---|---|
| Button | See how this page looks | לראות איך הדף ייראה | شاهد كيف ستبدو هذه الصفحة |
| Banner | Example: a test shop, not your data. Nothing here can be approved, saved or sent. | דוגמה: חנות לבדיקה, לא הנתונים שלך. כאן אי אפשר לאשר, לשמור או לשלוח דבר. | مثال: متجر تجريبي، وليست بياناتك. لا يمكن هنا اعتماد أي شيء أو حفظه أو إرساله. |
| Close | Close the example | סגירת הדוגמה | إغلاق المثال |
| Tag | Example | דוגמה | مثال |

## What the repository owner is asked

Approve the screens and the words, or say what to change.
