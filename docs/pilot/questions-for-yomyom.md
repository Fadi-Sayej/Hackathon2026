# Questions for YomYom — pilot setup

> **2026-09-27 (D-23):** the pilot with the YomYom store has ended. Kept as the record of
> what was asked; nothing here is to be sent.

**Owner:** Malik (task D-0) · **Send by:** immediately · **Handover:** 13/08/2026

Everything here comes from actually reading their export (`all4shop_Mlai.csv`, 7,674 rows). The
specifics matter — a manager answers "why does espresso show −9,871?" far more readily than
"can you tell us about your data quality".

> **Do not send all of this in one message.** Send **Part 1** now (3 questions, 30 seconds to
> answer). Send Part 2 once they reply, or bring it to the training session. A busy shop manager
> who receives fourteen questions answers none of them.

---

## PART 1 — Send now. Blocking.

These three decide whether the core feature works at all.

### 1. Can your system export **sales**, not just current stock?

**What we need:** any report showing *what was sold and when* — daily sales, receipts, item
movement, a Z-report. Even a rough one. Ideally a sample file so we can check the format.

**Why:** the file you sent shows how much stock you have **right now**, but not what sold. Without
sales history we cannot tell you what's running out, what to reorder, or what's selling slowly —
those are the features the system is built around. Everything else we can work around; this one
we can't.

**If the answer is no:** we work it out by comparing stock levels day to day (see Q2). That works,
but it needs the daily file.

### 2. Can you send the stock export **once every morning**?

**What we need:** the same file you already sent, once a day, ideally at a consistent time.

**Why:** if we get the file daily, we can work out what sold by comparing yesterday's stock to
today's. If yesterday a product showed 40 units and today it shows 33, roughly 7 were sold. That
becomes your reorder recommendations. **The more often the file arrives, the more accurate every
number in the system becomes** — and if it arrives irregularly, our estimates get noticeably
weaker, so we would rather promise you less.

It takes about 30 seconds. If it's easier, we can set up an automatic scheduled export or a shared
folder so you don't have to think about it.

### 3. How would you prefer to send it?

WhatsApp, email, a shared folder (Google Drive / Dropbox), or an automatic export from the POS?

**Why:** we'll build around whatever is least effort for you. If it's a chore, it won't happen
daily, and then the system quietly gets worse over the trial.

---

## PART 2 — Understanding your data

We found these while preparing your data. Most are probably normal for how you work — we want to
confirm rather than guess, because guessing wrong means showing you wrong numbers.

### 4. Negative stock — 627 products

Examples straight from your file:

| Product | Stock shown |
|---|---|
| מאפה קטן יח | **−35,942** |
| אספרסו | **−9,871** |
| קפוצינו רגיל | **−8,070** |
| אספרסו כפול | **−3,148** |
| כוס קרח | **−2,438** |

**Our guess:** these are things you *make and sell* but never *receive into stock* — coffee,
pastries, ice. The system subtracts one on every sale but nothing ever adds stock back, so the
number keeps falling. If so, **−35,942 is really a count of how many you've sold**, which would
actually be useful to us.

**What we need to know:** is that right? And is the counter ever reset?

**Why it matters:** if these are sales counters, they're some of the best sales data you have and
we'd use them directly. If instead they mean something else — stocktake corrections, an error —
we must exclude them, because otherwise we'd report huge phantom sales.

### 5. Products with no cost price — 1,270 products

Examples: `שוקו חם גדול`, `שטיפה פסח חיצונית / פנימית`, `פריט כללי - וולט`.

**What we need:** is the cost genuinely unknown, or just not filled in?

**Why:** we calculate profit as selling price minus cost. With no cost we can't tell you your
margin on those items, and we can't warn you if you're selling something below what it cost you.
We'd rather show nothing than show a made-up margin.

Several look like **services** (car wash) or **items made from other items** — for those, "no cost
price" is expected and we'll handle them separately. Just confirm.

### 6. Products with a zero selling price — 223 products

Examples: `משטח עץ מחוטא` (wooden pallet), `ארגז מתקפל 5319 ירוק` (folding crate), `משטח יורו`.

**Our guess:** returnable packaging or deposit items, not things a customer buys.

**What we need:** confirm, so we exclude them from recommendations instead of reporting them as
mispriced.

### 7. Products with no barcode — 307 products

Examples: `כוס קפה שחור`, `אייס בראד`, `חלב רגיל - עובדים`, `כולמוביל מימון שטיפה`.

**What we need:** what kind of items are these?

**Why:** we compare your prices to nearby shops by matching barcodes. No barcode means no
comparison — that's fine if they're prepared items, staff consumption, or services, but we want to
be sure we're not missing real products.

### 8. What is the `WOLT` column?

It's filled in on 6,411 of your products, and in the ones we checked it matches your normal
selling price exactly.

**What we need:** is this the price you list on Wolt? Is it maintained, or was it copied once from
the shelf price?

**Why:** if it's a real, maintained Wolt price we can flag where your delivery price and shelf
price have drifted apart. If it was copied once and never updated, we'd be reporting differences
that don't exist.

### 9. What does item type `מכלול` mean? (18 products)

Everything else is `רגיל`. We assume `מכלול` means an item assembled from other items (like
`שוקו חם גדול`). Confirm?

---

## PART 3 — About the trial itself

### 10. Who will actually use this — you, or your staff too?

**Why:** the screens are currently in English, with your product names in Hebrew. That's fine if
it's mainly you using it. If your staff on the floor will use it, we should put the whole interface
in Hebrew or Arabic — tell us which, and we'll do it before the trial.

### 11. What's the thing that costs you the most today?

Running out of popular items? Products expiring on the shelf? Not knowing whether your prices are
competitive? Money tied up in stock that doesn't sell?

**Why:** we can show you many things. We'd rather do the one that matters to you properly than
five of them badly.

### 12. How do you decide what to reorder today?

Walking the shelves? Experience? A report from the system?

**Why:** we need to fit into how you already work. And to prove the system helped, we need to
understand what "before" looked like.

### 13. Do you record expiry dates anywhere?

**Why:** your export doesn't include them, and expiry is one of the clearest ways a shop loses
money. We've built a way to record an expiry date in a few seconds on a phone when goods arrive —
but only if that fits your routine. Do you currently track it at all, even on paper?

### 14. Two practical things

- **Roughly how much do you throw away each month** because it expired or didn't sell? A rough
  figure is fine — we need a "before" number, otherwise we can't show you at the end whether we
  actually helped.
- **When can we come in for 20 minutes** to show you the system and set up the daily routine? And
  who is the best person for us to contact day to day?

---

## Notes for us (do not send)

- Q1 and Q2 are the only true blockers. Everything else improves accuracy or the story.
- Q4 is the highest-value question here. If those negative numbers are cumulative sales counters,
  we get real sales data for the fastest-moving items in the shop — coffee and bakery — without
  waiting for a sales export at all.
- Q10 decides whether Anas's C-1 stays a small job (English UI, Hebrew data) or becomes a full
  RTL translation. **Ask before he starts.**
- Q14's waste figure is the pilot baseline (`PLAN.md` §5). Without a "before" number, nothing we
  report at the end can be attributed to us.
- Send Part 1 today. Every day without a second export is a day the velocity engine cannot be
  proven on real data before handover.
