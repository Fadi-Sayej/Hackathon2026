---
ID: F8-S1
Title: Order Quantity — what to order, and how much, for the next order
Status: Ready for review
Owner: smartshelf-architect
Version: 0.5 (2026-09-25, D-21: the market boost is a model's pick)
Parent: [F8 — Order Quantity](../intent.md)
Related Intents: INT-004, INT-010
Inputs: [docs/features/F8-order-quantity/intent.md, docs/product/PRD.md §5 §6 §7 §10, docs/product/intent-register.md (D-1, D-3, D-7, D-8, D-10, D-16, D-18, D-19, D-20, D-21), docs/features/gaps-and-open-questions.md (GAP-008, GAP-009), F2-S1, F5-S1, F7-S1, F10 intent, ADR-001, ADR-002, ADR-003, ADR-004, ADR-005, ADR-007, ADR-008, ADR-009, ADR-011, ADR-012, ADR-014, ADR-016, ADR-017, ADR-024, ADR-027, ADR-028, CLAUDE.md, the repository owner's answers of 2026-09-25 (§17), public/data/dashboard.json and catalogue.json (generated 2026-09-24T02:46Z), data/internal/silver_pos/*.parquet]
Answered by: [System Design](../../../architecture/system-design.md) §21 — a placeholder until V2's first design round
Updated: 2026-09-25
---

# F8-S1 — Order Quantity

> **The first V2 spec, and what it rests on.** It turns D-18 … D-21 into requirements, and
> the four answers the repository owner gave on 2026-09-25 (§17: OQ-901 … OQ-903, OQ-908).
> It can be reviewed and designed now. **It cannot publish a single quantity until the store
> owner supplies three things that do not exist today:**
> - **sales and deliveries per product per day**, from his POS;
> - the **days he orders** each department;
> - how long each department's products **keep**.
>
> Until then the Reorder entry keeps saying what it waits for (FR-160). That is deliberate:
> every shorter path found while writing this spec needed a number nobody has (§21).

Implements intent F8. Bound by ADR-001, ADR-003, ADR-005, ADR-007, ADR-008, ADR-009,
ADR-011, ADR-012, ADR-014, ADR-016, ADR-027 and ADR-028, and by settled decisions D-1, D-3,
D-7, D-8, D-10, D-16, D-18, D-19, D-20 and D-21.

---

### 1. Purpose

Tells the owner, product by product, how many to order on each department's next order day.
The quantity is:
- **set by his own sales** (D-19);
- **raised by a boost a model picks for the product, from 0% to 25%,** when the stores near
  him run out (D-18, D-21);
- **capped** by what sells before it spoils, using the shelf life he states (F10, OQ-908);
- **reduced by his stock** only when the count is recent and checks out (OQ-902).

Where the evidence cannot support a number, it shows none (D-3). It never writes to his
point-of-sale system (D-7), never puts a ₪ figure on a suggestion (D-1), and never fills an
unknown with a guess: not an order day, not a shelf life, not a missing day's sales.

---

### 2. Intent Traceability

| Intent | This spec |
|---|---|
| INT-004 — «ماذا أطلب اليوم وبأي كمية؟» | FR-143 … FR-163 |
| INT-010 — "Complete my missing data — with minimum disturbance" | FR-157 … FR-159. Only his disagreement answers are asked on screen; the store facts are gathered once |
| INT-PROV — every figure recomputable | FR-154. F7-S1 governs every figure here in full |

It also serves:
- **PRD §5:** V2, «الطلب من السوق».
- **PRD §6 #3:** V2 "recommends confidently on what moves, and stays silent about the long
  tail rather than guessing" (FR-145, FR-155).
- **PRD §7:** the POS export commitment, which F8 depends on (OQ-904).

---

### 3. Scope

#### In Scope

- A quantity per product for its department's next order day, for products with enough of
  his own sales (D-19).
- The market adjustment: a boost a language model picks for the product, from 0% to 25%,
  when the market of D-18 runs out of it (D-21).
- Reducing it by his stock, only when the count is recent and checks out (OQ-902).
- A shelf-life cap from the shelf life he states for the department (OQ-908), or later from
  F10.
- The store facts F8 needs from him: each department's order schedule and shelf life,
  gathered once and recorded as his (FR-157).
- The disagreement question between the market and his own sales (D-19, D-20).
- The existing Reorder and Approved orders entries (OQ-901): suggestions, approve, change or
  dismiss, and a list of approved lines he can export.

#### Out of Scope

- Writing anything to his point-of-sale system (D-7).
- Any ₪ figure on a suggestion or on an approved line, and any ₪ total (D-1, ADR-012).
- Entries on the daily surface. Suggestions appear on Reorder only (OQ-901).
- Supplier grouping, supplier lead times and supplier order days. No supplier is recorded
  for any product he sells, and lead times are F11 (V3).
- Measuring shelf life. That is F10.
- The reason written as a sentence. That is F14 (D-15, D-16); F8 publishes the facts it
  will be written from.
- Letting a disagreement answer change a quantity. D-20 leaves that for later.
- Products he does not stock (§5): whether to carry them is F9's question (INT-005), whose
  decision stays open.
- Seasonal forecasting (PRD §6 #5), and pack or case sizes, which are not recorded.

---

### 4. Actors and Triggers

| Actor | Trigger | Frequency |
|---|---|---|
| Engine | The nightly run publishes suggestions from the inputs that landed | Nightly (ADR-007) |
| Store owner | Opens Reorder; approves, changes or dismisses suggestions | On each department's order days |
| Store owner | Answers a disagreement question | When presented, at most three questions at a time (D-8) |
| Team, with the store owner | Records each department's order schedule and shelf life | Once, and again whenever he changes them |
| Team or store owner | Delivers the POS export of sales and deliveries per day | Per the owner commitment (PRD §7). Its cadence is open (PRD §10, OQ-904) |

---

### 5. Domain Terms

| Term | Definition |
|---|---|
| **Order schedule** | When the store owner orders a department, as he states it (OQ-903). It is either weekdays (every day; Sundays; Sundays and Wednesdays), or a fixed interval from a stated first date (every 14 days from 4 October), or "no fixed days". Never inferred and never defaulted |
| **Next order day** | A department's first scheduled order day on or after the run's date |
| **Order cycle** | The days from the next order day up to, but not including, the scheduled day after it. What a suggestion must cover |
| **Shelf life** | How many whole days a department's products keep, as the store owner states it (OQ-908). Once F10 exists, it is also what F10 measures (FR-151). "Does not spoil" is a statement too |
| **Report day** | A day for which the POS export of that day's sales and deliveries per product was received |
| **Evidence window** | The 28 days ending on the latest report day, which must be no more than 7 days before the run (FR-144). Days with no report are left out. Its **weeks** are the four 7-day blocks counted back from its last day |
| **Moving product** | One that sold in each of the window's four weeks (FR-145) |
| **Daily mean** | The units a product sold on the window's report days, divided by the number of those days: a mean of observed days, not a division of any report |
| **Boost** | The percentage a language model picks for a product, once a night, when the market is running out of it (D-21). Accepted only from 0% to 25% (FR-147, FR-164) |
| **Adjusted daily mean** | The daily mean times one plus the product's accepted boost, when the market is running out of it; otherwise the daily mean (FR-147) |
| **Expected sales** | The adjusted daily mean times the days in the order cycle (FR-146) |
| **The market** | The nearby stores at or above the format floor (D-18). Three today |
| **Running out** | The market's stockout classification for a product (FR-147, OQ-905) |
| **Usable count** | A recorded stock count at most 7 days older than the run, flagged by neither reconciliation nor hygiene, and followed by a report day for every day since it was taken (FR-149) |
| **Stock now** | A usable count plus the units delivered since it was taken, less the units sold since. A value below zero means the evidence is inconsistent, and the count is then not used |
| **Stock at the order day** | The stock now less the adjusted daily mean times the days from the run to the next order day, never below zero |
| **Gross quantity** | The expected sales, read as "you'll sell about X before your next order" |
| **Net quantity** | The expected sales less the stock at the order day, never below zero |
| **He stocks** | A product he stocks is one the window records a sale or a delivery of. In a department the evidence does not itemise (FR-156), it is one his latest recorded count shows above zero. Never F4's withdrawn class, which D-14 keeps off his screen |
| **Disagreement** | The market running out of a product he stocks but that is not moving (FR-158) |
| **Suggestion** | One product's quantity for its department's next order day, with the facts it was computed from |

---

### 6. Functional Requirements

#### Evidence

**FR-143** — Quantities come only from report days: sales and deliveries reported per product
per day. A longer report is never divided into days. So the seven monthly reports, today's
only sales evidence, supply no quantity at all (CLAUDE.md rules 5 and 13; ADR-028 §4), and
neither would a weekly one.

**FR-144** — The evidence window is the 28 days ending on the latest report day, and that
day must be no more than 7 days before the run.
- A day with no report is missing, not a day of zero sales, and is left out of every mean.
- The window exists only when it holds at least 21 report days, with at least one in each of
  its four weeks. One late or missing export therefore thins the evidence, but does not blank
  F8.
- The 28 days, the 21 days and the 7 days are policy values, all provisional (OQ-906). So the
  export must arrive at least weekly.

**FR-145** — A product is moving when it sold in each of the window's four weeks. Only a
moving product gets a quantity (D-19; PRD §6 #3).

**FR-146** — A moving product's expected sales are its adjusted daily mean, multiplied by the
days in its department's order cycle. An irregular schedule, such as Sundays and Wednesdays,
gives cycles of three and four days, and each suggestion covers its own.

#### The market adjustment

**FR-147** — When the market (D-18) is running out of a moving product, a language model
picks the product's boost, once a night (D-21).
- A pick from 0% to 25% is accepted. The product's daily mean is multiplied by one plus it,
  once, giving the adjusted daily mean that every expectation of this product then uses.
- A pick outside that range gives no boost at all, not a clipped one, and the suggestion says
  the pick was rejected.
- No pick, because the model was unavailable or the spending cap was reached, gives no
  boost, and the suggestion says why.
- A store below the format floor never triggers a boost, and neither does the national price
  file (D-18).

**FR-148** — The market adjustment can become unavailable on its own (ADR-014). When the
running-out signal cannot be computed, suggestions are still published, unadjusted, and
each says that the market signal was unavailable and why.

**FR-164** — The model is given only facts F8 publishes for the product (FR-154) and the
market's running-out facts: nothing it sees is absent from the artefact. It returns a
percentage and a one-line reason. Both are recorded and published with the suggestion,
labelled the model's estimate (D-10, D-21). Nothing else it returns is used (INV-079).

#### Stock

**FR-149** — A recorded stock count is used only when it is usable:
- at most 7 days older than the run;
- flagged by neither reconciliation nor hygiene (F2-S1);
- followed by a report day, with sales and deliveries, for every day since it was taken.

With a usable count, the stock now is the count plus the deliveries since, less the sales
since. A stock now below zero means the evidence is inconsistent, and the count is not used.
Otherwise the suggestion is net: the expected sales less the stock at the order day, which
deducts what will sell before the order day and never falls below zero.

Without a usable count, the suggestion is gross. It reads as he chose: "you'll sell about X
before your next order" (OQ-902). It then says why the count was not used, for example its
date.

**FR-150** — A product whose net quantity is zero is not suggested. The Reorder entry states
how many moving products the stock already covers.

#### Shelf life

**FR-151** — A product's quantity never exceeds what sells within its shelf life. The cap is
its adjusted daily mean times the whole days of shelf life, less the stock at the order day
when the count is usable.
- The shelf life is the one the store owner stated for the product's department.
- Once F10 exists, F10's own spec decides how its measured shelf lives combine with his
  statements.
- A shelf life of less than one day yields no quantity, and the suggestion says why.
- "Does not spoil" means no cap.

**FR-152** — A product whose department has no stated shelf life gets no quantity, and the
Reorder entry says the shelf life is needed (OQ-908). Nothing is defaulted. The category
table of starting guesses is not an input to F8.

#### The quantity

**FR-153** — A suggestion's quantity is the lesser of the need and the shelf-life cap
(FR-151), in the unit the sales report counts.
- The need is the net quantity with a usable count, and the gross quantity without one.
- A product whose expected sales for the cycle are below one unit gets no quantity. Less
  than one sells per cycle, so any whole quantity would be a guess about which cycle it sells
  in.
- A need is rounded to the nearest whole unit, halves up, so that over many cycles the units
  ordered match the units expected. Always rounding up would turn 1.14 a day into 2 a day.
- A quantity the cap sets is rounded down, so rounding never orders past what sells before
  it spoils. A cap that rounds down to zero or below yields no quantity, and the suggestion
  says why.
- It carries no ₪ figure (D-1).

**FR-154** — Every suggestion publishes the facts it was computed from:
- the department's order schedule, and the dates of the cycle it covers;
- the window's dates, and the units sold in each of its weeks;
- the daily mean;
- whether the market adjustment applied, and why not if it did not; when it did, the model's
  pick, its reason, the model it came from, and the adjusted daily mean;
- the expected sales;
- the recorded count, its date, and whether it was used and why;
- when used: the deliveries and sales since the count, the stock now, and the stock at the
  order day;
- the shelf life, its source, and whether it capped the quantity;
- whether the quantity is net or gross.

Each is recomputable (F7-S1). These are the facts F14 will explain (D-16).

#### No quantity

**FR-155** — A product gets no quantity, meaning not a zero and not a small number, when:
- it is not moving;
- its department has no order schedule, or its schedule is "no fixed days";
- its department's shelf life is not stated;
- no evidence window exists (FR-144);
- its expected sales for the cycle are below one unit;
- its shelf life is less than one day;
- the shelf-life cap rounds down to zero.

The Reorder entry says, per department, which of these holds (D-3).

**FR-156** — A department with no sales row at all in any evidence is not covered by the
evidence. It is never read as a department that sold nothing (ADR-011).
- Its products get no quantity, and the Reorder entry says the sales evidence does not
  itemise the department.
- D-19 still applies to them. Where the market runs out of a product he stocks, the FR-158
  question is raised in ADR-011's words.
- Counted in `catalogue.json` today, 17 of its 55 departments hold 225 products with no row in
  any of the seven monthly reports. Five of them hold 25 to 46 products each (GAP-009).

#### The store facts

**FR-157** — A department's order schedule and its shelf life are facts only the store
owner holds.
- The team gathers them from him once, and records them as his statements.
- They are never defaulted, inferred, or copied from another department (OQ-903, OQ-908).
- "I don't know" leaves a fact unstated, and FR-155 then applies. So does "no fixed days".
- F8 raises no on-screen question for either fact. They are two facts per department,
  gathered once. In the three-question panel they would wait behind every question with a ₪
  figure (ADR-027), of which there are 11 today.

#### The disagreement question (D-19, D-20)

**FR-158** — When the market is running out of a product he stocks that is not moving,
including one with no sales row in the window, F8 publishes no quantity for it (D-19). It
raises one question instead.

It is raised only when an evidence window exists (FR-144), because "not moving" is measured
over it. The one exception is FR-156's department, whose products have no row in any
evidence at all.

The question states only what was observed:
- that the stores near him ran out of the product;
- his units in the window, or that his sales evidence has no row for it (ADR-011).

It asks why:
- the product's place on the shelf;
- its price;
- a weak market for it here (intent §6);
- or that it sells, but not through these reports (FR-156).

It never claims the market sells a lot of the product, because competitor volumes are not
observed (§21).

**FR-159** — His answer is saved in owner state (ADR-003) and retires that product's
disagreement. It is never raised again, even when the facts later change, and it changes no
quantity (D-20). He can still revise it (F5-S1 FR-090).

This is the question kind's FR-081 and FR-093 treatment, which ADR-027 requires of a new kind
of question:
- only he knows why;
- nothing consumes the answer except the retirement.

#### Reorder and Approved orders

**FR-160** — Suggestions appear on the existing Reorder entry (ADR-028 §1), grouped by
department, and nowhere else: they are not entries on the daily surface (OQ-901). While F8
cannot publish, the entry keeps saying what it waits for, and names the missing input or
fact.

**FR-161** — For each suggestion he can approve it as suggested, approve it with his own
quantity, or dismiss it.
- His quantity is authoritative (F5-S1 FR-087), and is recorded beside the suggested one.
- Outcomes are owner state (ADR-003), keyed on the product and the order day the suggestion
  is for (ADR-009). That key is the same on every night before the day.
- The outcome snapshot carries its signal family (ADR-016).

**FR-162** — Approved lines appear on the existing Approved orders entry, grouped by
department. Each shows the product, the quantity and the order day; there is no unit cost,
subtotal or total (D-1, ADR-012). He can export the lines as a CSV to give his suppliers.
Nothing is written to his point-of-sale system (D-7).

**FR-163** — A suggestion is for its department's next order day. It is the same entry every
night until that day, and an approval or a dismissal holds for it. Once the day has passed,
the next order day's suggestion is a new entry, and nothing carries over to it.

---

### 7. Behavioral Invariants

**INV-069** — No suggestion, approved line or export carries a ₪ figure, and no ₪ total is
shown anywhere (D-1, ADR-012). A violation would read: "estimated order total ₪…" on Approved
orders. A count of products is not money.

**INV-070** — No quantity is derived by dividing a report into shorter periods, or from a
monthly or weekly report. A violation would read: a weekly quantity equal to a month's units
divided by 4.3.

**INV-071** — No order schedule, cycle or shelf life is defaulted, inferred from a category
table, or copied from another department. An unstated fact yields no quantity, and the
suggestion says so (D-3; OQ-903, OQ-908).

**INV-072** — A day with no report is never read as zero sales. A department with no row in
the evidence is never read as one that sold nothing (ADR-011).

**INV-073** — A recorded count that is not usable is never subtracted. A usable one is
subtracted only through the stock now, meaning deliveries added and sales deducted since it
was taken, and never when that stock now is below zero.

**INV-074** — The market adjustment is applied at most once per suggestion, by exactly the
recorded, accepted pick, and only from the market of D-18. A pick outside 0% to 25% is never
applied, not even in part (D-21).

**INV-075** — A disagreement is raised at most once per product, and never without an
evidence window except in FR-156's case. Once answered it is never raised again, and its
answer never changes a quantity (D-20).

**INV-076** — A product that is not moving, or that sells less than one unit per cycle,
never receives a quantity, whether zero or small (D-19, D-3).

**INV-077** — Nothing F8 does writes to the owner's point-of-sale system (D-7).

**INV-078** — The same order is never suggested twice. A department's suggestion for an order
day is one entry, however many nights it is published.

**INV-079** — The model moves one number only: the boost, within 0% to 25%. Nothing else it
returns is used as a figure. It cannot set a quantity, a count, a shelf life or a date. That
is the failure F14's intent records, a model turning "order 20" into "25", closed by
construction.

---

### 8. Behavioral Scenarios

**SCN-132 — Only the monthly reports**
GIVEN the only sales evidence is the seven monthly reports
WHEN the engine runs
THEN no quantity is published, and Reorder says it waits for sales and deliveries reported per day.

**SCN-133 — A gross suggestion**
GIVEN a complete 28-day window, a department ordered on Sundays with a stated shelf life of 90 days, a product sold in each of the window's weeks, no market signal, and a recorded count from 6 June
WHEN the engine runs on a Thursday
THEN the suggestion is for Sunday and covers seven days at the daily mean. It is gross — "you'll sell about X before your next order" — and says the count was not used because it is older than 7 days.

**SCN-134 — A net suggestion**
GIVEN the same, with a count taken three days before the run that neither reconciliation nor hygiene flags, and report days since it
WHEN the engine runs on Thursday
THEN the stock now is the count plus the three days' deliveries less their sales, the stock at Sunday deducts Thursday to Saturday at the daily mean, and the suggestion is the expected sales less that, never below zero.

**SCN-135 — A flagged count**
GIVEN a recent count for a product that reconciliation flags
WHEN the engine runs
THEN the suggestion is gross, and names the flag as the reason the count was not used.

**SCN-136 — The market runs out**
GIVEN the market's signal says it is running out of a moving product
WHEN the engine runs and the model picks 10% for it
THEN the published facts show the daily mean, the pick with its reason, and the adjusted daily mean 10% higher, once, and the suggestion says why.

**SCN-137 — Market signal unavailable**
GIVEN the nearby stores' snapshots cannot be read
WHEN the engine runs
THEN suggestions are published unadjusted, each saying the market signal was unavailable, and no disagreement is raised.

**SCN-138 — Shelf life caps the quantity**
GIVEN a department ordered on Sundays and a stated shelf life of 2 days
WHEN the engine runs
THEN its quantity is at most two days at the adjusted daily mean, less the stock at the order day if known, rounded down, and the suggestion says it was capped.

**SCN-139 — Shelf life of less than a day**
GIVEN a department whose products the store owner says keep less than a day
WHEN the engine runs
THEN its products get no quantity, and each says the shelf life is shorter than the evidence can size an order for.

**SCN-140 — Order schedule not stated**
GIVEN a department whose order schedule has not been recorded, or is "no fixed days"
WHEN the engine runs
THEN its products get no quantity, no on-screen question is raised, and Reorder says the department's order schedule is needed.

**SCN-141 — Disagreement**
GIVEN a complete window, and the market running out of a product he sold in only one of its four weeks
WHEN the engine runs
THEN no quantity is published and one question is raised, stating what was observed. Once he answers, it is never raised again and no quantity changes.

**SCN-142 — A department the reports do not itemise**
GIVEN a department with no row in any sales report, and the market running out of one of its products that he stocks
WHEN the engine runs
THEN its products get no quantity, Reorder says the evidence does not itemise the department, and one question is raised for that product, saying his sales evidence has no row for it and offering "it sells, but not through these reports".

**SCN-143 — Approve with his own quantity**
GIVEN a suggestion of 12 for Sunday
WHEN he approves it with 20
THEN Approved orders lists 20 for Sunday, and the suggested 12 is recorded beside it.

**SCN-144 — A missing day**
GIVEN one day's report is missing inside the latest 28 days
WHEN the engine runs
THEN that day is left out of every mean and suggestions continue. Only fewer than 21 report days, a week with none, or a latest report day more than seven days old leaves no window, and then Reorder says which.

**SCN-145 — The same order, several nights**
GIVEN a department ordered on Sundays, and a suggestion he approved on Thursday
WHEN the engine runs on Friday and Saturday
THEN the same entry is published with its approval, and no second suggestion for Sunday appears. On Sunday night, the next Sunday's suggestion is a new entry.

**SCN-146 — Shelf life not stated**
GIVEN a department with an order schedule recorded but no shelf life
WHEN the engine runs
THEN its products get no quantity, and Reorder says the department's shelf life is needed.

**SCN-147 — Stock now below zero**
GIVEN a usable-looking count of 20 taken five days ago, and five report days that show 100 units sold and no deliveries
WHEN the engine runs
THEN the stock now would be below zero, so the count is not used, and the suggestion is gross and says the stock evidence is inconsistent.

**SCN-148 — No window, no disagreement**
GIVEN no complete 28-day window, for example only the monthly reports or a late export
WHEN the market is running out of products he stocks
THEN no disagreement is raised, except for products in a department with no row in any evidence (SCN-142).

**SCN-149 — Less than one per cycle**
GIVEN a department ordered every day, and a product sold in each of the window's weeks at about two a week
WHEN the engine runs
THEN its expected sales for the one-day cycle are below one unit, so it gets no quantity, and Reorder says it sells less than one per cycle.

**SCN-150 — A pick above the limit**
GIVEN the market is running out of a moving product
WHEN the engine runs and the model picks 40% for it
THEN no boost is applied, not even 25%, and the suggestion says the pick was rejected as above the 25% limit.

**SCN-151 — The model is unavailable**
GIVEN the market is running out of moving products, and the model cannot be reached or the month's spending cap is reached
WHEN the engine runs
THEN suggestions publish without a boost, each saying why.

---

### 9. Inputs and Observable Outputs

| Input | Source | Required? |
|---|---|---|
| Sales and deliveries per product per day | The POS export (PRD §7; OQ-904), a new import. The monthly reports serve no quantity (FR-143) | Yes. Without it, no quantity |
| Each department's order schedule and shelf life | The store owner's statements, gathered by the team and recorded as his (FR-157) | Yes, per department |
| Recorded stock and its date | The POS export, as F2-S1 reads it | No. Without a usable count, the suggestion is gross |
| Reconciliation and hygiene flags | F2-S1 | No. Needed only to use a count |
| The market's running-out signal | The daily delivery snapshots of the D-18 stores (OQ-905) | No. Without it, no adjustment and no disagreement |
| The boost per product | A language model, nightly, on a paid account under a monthly spending cap (D-21). The configured `stockout_demand_lift` of 1.15 is no longer used | No. Without an accepted pick, no boost |
| Catalogue membership, department and stock | The published catalogue (ADR-024) | Yes |
| His disagreement answers and outcomes | Owner state (ADR-003) | No |

| Output | Where it is observable |
|---|---|
| Suggestions with their facts, and per-department reasons for no quantity | The artefact; the Reorder entry |
| Disagreement questions | F5's question panel |
| Approved lines | The Approved orders entry, and its CSV export |

---

### 10. State / Lifecycle Semantics

The engine recomputes suggestions every run and stores none of them (ADR-004). What
persists is the owner's.

| Thing | Transitions | Persists? |
|---|---|---|
| Suggestion | published, the same entry every night until its order day → approved (as suggested, or with his quantity) or dismissed | The outcome does, keyed on the product and the order day. Nothing carries to the next order day (FR-163) |
| Order schedule, shelf life | unstated → stated → revised | Yes, as his statements. Never overwritten by inference |
| Disagreement | raised → answered → retired | Yes, in owner state. Never reopened (D-20) |

---

### 11. Failure and Recovery Behavior

| Condition | Required behavior |
|---|---|
| No report days, or no window within the freshness limit | The capability is unavailable and names the missing input; Reorder says what it waits for (FR-160). An empty list is a failure, not a result (CLAUDE.md rule 10) |
| Some export days missing | Those days are left out of the mean (FR-144). Below 21 report days, or with a week that has none, there is no window, and Reorder names the missing reports |
| A department's order schedule or shelf life not stated | No quantity for that department. Reorder names the missing fact (FR-155) |
| Deliveries missing from a report day | No count taken before that day is usable. The suggestion is gross (FR-149) |
| Stock now below zero | The count is not used; the suggestion is gross and says the stock evidence is inconsistent (FR-149) |
| Market snapshots missing or unclassifiable | The adjustment becomes unavailable on its own; suggestions still publish (FR-148) |
| Model unavailable, or the monthly spending cap reached | No boost. Suggestions still publish, each saying why (FR-147) |
| A pick outside 0% to 25%, or not a number | No boost, not a clipped one. The suggestion says the pick was rejected (FR-147) |
| Owner state unreachable | As ADR-003 and ADR-017 define: the run is degraded, and the answers and outcomes it uses are those of the last owner state it holds, stated with that state's date |

---

### 12. Edge Cases

| Case | Behaviour |
|---|---|
| An irregular schedule, such as Sundays and Wednesdays | Cycles of three and four days. Each suggestion covers its own cycle (FR-146) |
| An interval schedule, such as every 14 days from a stated date | Its order days follow from the first date. Each cycle is 14 days |
| "No fixed days" or "I don't know" | The department gets no quantity until a schedule is stated (FR-157) |
| He says a department's products do not spoil | No shelf-life cap for that department (FR-151) |
| The run is not on an order day | The suggestion is for the next order day, and a net one deducts what sells before it (FR-149) |
| Goods sold by weight | The quantity is in the report's unit, rounded to a whole unit of it (FR-153) |
| A product with no sale and no delivery in the window | He does not stock it (§5): not suggested, and raises no disagreement. Whether to carry it is F9's question |
| A day the store is closed and sends no export | A missing day, left out of the mean. Regular closing days inside a cycle would make its expected sales too high (OQ-906) |
| Net quantity of zero | Not suggested; counted as covered by stock (FR-150) |
| He changes a department's schedule | The next run uses it. Earlier outcomes keep their order days |
| A disagreement product that later starts moving | It gets a quantity. If he already answered, the disagreement stays retired |

---

### 13. Non-Functional Requirements

**NFR-066 (Determinism)** — The same inputs, policy, store facts, owner state and recorded
boosts produce the same suggestions, questions and facts. The model's picks themselves are
not deterministic, which is why each is recorded (D-21).

**NFR-067 (Recomputability)** — Every quantity is reproducible from its published facts,
the recorded boost included, by the engine in print mode (ADR-002, F7-S1). The boost is
replayed from its record, never recomputed from the evidence (D-21).

**NFR-068 (Owner effort)** — F8 asks on screen only about disagreements, at most once per
product (D-20), within D-8's limit. The store facts are gathered once, not asked in the panel
(FR-157).

**NFR-069 (No runtime)** — Suggestions are computed in the nightly run. The page computes
nothing (ADR-001, ADR-007).

---

### 14. Compatibility and External Constraints

**C-63** — ADR-001: the engine computes every quantity. The browser renders suggestions and
records his outcomes.

**C-64** — ADR-005 and ADR-014: F8 publishes through the capability contract, and the market
adjustment is a separately-unavailable unit.

**C-65** — ADR-003: his disagreement answers and outcomes are owner state. The browser writes
them and the engine pulls them; the engine never writes them back.

**C-66** — ADR-008 and D-18: only stores at or above the floor may move a quantity. Below
it, a store is context only (F3-S1 C-21).

**C-67** — D-20 governs F8's disagreement question. Where it differs from F5-S1, D-20
prevails, because a settled decision outranks an approved spec. It differs on:
- FR-080 and INV-044: the answer changes no quantity;
- FR-088: the answer takes effect only by retiring the disagreement;
- FR-089: a changed fact does not re-open the question;
- FR-082a: an idle product is stocked and does not sell, which is exactly D-19's case, so it
  may be asked about;
- F5-S1's out-of-scope line on his commercial reasoning: the question asks why.

FR-082 still holds, and D-19 does not override it. A product he does not stock (§5) has no
sale and no delivery in the window, so asking why it does not sell becomes asking whether to
carry it. That is F9's question, and D-20 leaves it open. The test is his stocking, read
from the window, and never F4's withdrawn class, because D-14 keeps anything that depends on
automatic withdrawal off his screen.

Otherwise F5-S1 applies: FR-084 (three at once), FR-086, FR-087, FR-090 and FR-091.

**C-68** — ADR-027: the disagreement question carries no ₪ figure, so it is ordered after
every question that has one. Today that means after all 11 open questions in the artefact,
each of which has a figure. Among its own kind it is ordered by units sold in the window,
then by barcode, which is ADR-027's tiebreak; each question is about one barcoded product.

**C-69** — ADR-011: a missing report or a missing row is stated as such ("no sales row"),
never as "zero sales".

**C-70** — ADR-028: F8 lights the existing Reorder and Approved orders entries, and does so
on real per-day demand, not on the monthly reports (§4).

**C-71** — F7-S1 and D-21: the boost is a figure whose source is a model, not the evidence.
It is published as an input with provenance: the model, the date, and the facts it was given.
It is labelled the model's estimate before it can be questioned (D-10). Where F7-S1 would
require recomputation from the evidence, D-21 prevails and the figure is replayed from its
record.

**C-72** — D-16 and ADR-007: D-16 governs only F14's reason sentence. The boost is one of the
suggestion's published facts, so that sentence may cite it. The model runs only in the
nightly run, never at request time, and on a paid account under a monthly spending cap
(D-21).

---

### 15. Acceptance Criteria

**AC-136** — With only the monthly reports, no quantity is published, and Reorder names the
missing input. *(FR-143, FR-160, INV-070, SCN-132)*

**AC-137** — No quantity comes from a report longer than a day, and none equals such a
report's units divided into days. *(FR-143, INV-070)*

**AC-138** — A missing day never counts as zero sales: it is left out of the mean. The
window needs at least 21 report days, one in each week, and must end within 7 days of the
run. *(FR-144, INV-072, SCN-144)*

**AC-139** — A product that did not sell in each of the window's four weeks has no quantity,
not a zero. *(FR-145, FR-155, INV-076)*

**AC-140** — The published daily mean equals the units sold on the window's report days
divided by their number, and the expected sales equal the adjusted daily mean times the days
in the cycle. A need is rounded to the nearest unit. *(FR-146, FR-153, FR-154, NFR-067)*

**AC-141** — When the market is running out and the model's pick is accepted, the published
adjusted daily mean equals the daily mean times one plus the recorded pick, applied once. A
store below the floor never produces an adjustment. *(FR-147, INV-074, SCN-136)*

**AC-142** — With the market signal withheld, suggestions still publish, unadjusted, each
saying why, and no disagreement is raised. *(FR-148, SCN-137)*

**AC-143** — A count older than 7 days, flagged by reconciliation or hygiene, or not followed
by report days with deliveries is never used. The gross suggestion then reads in his words
and says which of these applied. *(FR-149, INV-073, SCN-133, SCN-135)*

**AC-144** — With a usable count, the stock now is the count plus the deliveries since less
the sales since. The stock at the order day deducts the days before it, never below zero, and
the net quantity is the expected sales less it, never below zero. A zero is not suggested,
and is counted as covered. *(FR-149, FR-150, INV-073, SCN-134)*

**AC-145** — A stated shelf life caps the quantity at whole days, less the stock at the order
day, rounded down. Less than a day, or a cap that rounds to zero, yields no quantity.
*(FR-151, FR-153, SCN-138, SCN-139)*

**AC-146** — No order schedule, cycle or shelf life is defaulted. A department missing either
fact, or scheduled "no fixed days", has no quantity, and Reorder names the missing fact.
*(FR-152, FR-155, FR-157, INV-071, SCN-140, SCN-146)*

**AC-147** — A department with no row in the evidence gets no quantity, and Reorder says the
evidence does not itemise it. *(FR-156, INV-072, SCN-142)*

**AC-148** — No suggestion, approved line or export carries a ₪ figure, and no ₪ total is
shown. *(FR-153, FR-162, INV-069)*

**AC-149** — Every suggestion publishes the facts of FR-154, each recomputable. *(FR-154,
NFR-066, NFR-067)*

**AC-150** — Disagreement questions never make more than three on screen at once, counting
every other question. They are ordered after every question with a ₪ figure, then by units
sold and barcode. *(FR-158, C-67, C-68)*

**AC-151** — A disagreement question states only what was observed, in ADR-011's words, and
is raised once per product. Once answered, it is never raised again and changes no quantity.
*(FR-158, FR-159, INV-075, SCN-141)*

**AC-152** — Approving with his own quantity lists his quantity on Approved orders for that
order day, with the suggested one recorded. *(FR-161, FR-162, SCN-143)*

**AC-153** — The Approved orders export holds the product, barcode, quantity and order day,
and nothing is written to the point-of-sale system. *(FR-162, INV-077)*

**AC-154** — A department's suggestion for an order day keeps one entry id on every night
before that day. An approval given on one night is still shown on the next, and no second
suggestion for the same order day appears. *(FR-161, FR-163, INV-078, SCN-145)*

**AC-155** — In a department the reports do not itemise, the market running out of a product
he stocks raises the FR-158 question, saying his sales evidence has no row for it. *(FR-156,
FR-158, C-69, SCN-142)*

**AC-156** — F8 raises no on-screen question about order schedules or shelf life. *(FR-157,
NFR-068, SCN-140)*

**AC-157** — A stock now below zero is never used. The suggestion is gross and says the stock
evidence is inconsistent. *(FR-149, INV-073, SCN-147)*

**AC-158** — Without an evidence window, no disagreement is raised, except in a department
with no row in any evidence. *(FR-158, INV-075, SCN-148)*

**AC-159** — A product expected to sell less than one unit in its cycle gets no quantity.
*(FR-153, FR-155, INV-076, SCN-149)*

**AC-160** — Every boost is published with the model's pick, its reason and the model it came
from, labelled the model's estimate. The quantity replays from the recorded pick. *(FR-154,
FR-164, NFR-067, C-71)*

**AC-161** — A pick above 25% or below 0% gives no boost, not a clipped one, and the suggestion
says the pick was rejected. No pick gives no boost, and says why. No figure other than the
boost is ever taken from the model. *(FR-147, INV-074, INV-079, SCN-150, SCN-151)*

---

### 16. Assumptions

**ASM-064** — His POS can export sales and deliveries (כניסות מלאי) per product per day. The
monthly reports carry both columns, which is why this is plausible, but a per-day export is
unverified. If it cannot be had, F8 publishes no quantity (FR-143). *(OQ-904)*

**ASM-065** — Within a department the report itemises, a product absent from a day's report
sold nothing that day. This is GAP-009's reading. FR-156 confines it to departments that
appear in the evidence at all, and it is to be confirmed with the owner for the daily reports
before release.

**ASM-066** — His order rhythm follows the department. No supplier is recorded for any of
the 1,518 products he sells (`yomyom_products.parquet`). If his rhythm follows the supplier
instead, the grouping changes once suppliers are recorded.

**ASM-067** — Recent sales predict the next cycle. Nothing seasonal is measurable from seven
months (PRD §6 #5). Ramadan and the summer peaks can falsify this, which is why the window's
dates are published, so the age of the evidence is visible.

**ASM-068** — The units he orders are the units the report counts. Pack and case sizes are
not recorded.

**ASM-069** — A department's products keep about as long as he says the department's do.
F10 will measure per product.

**ASM-070** — An order placed on an order day arrives that day. Lead times are F11 (V3). A
later delivery would leave the cycle's first days uncovered.

**ASM-071** — A recorded count reflects the end of its date. The sales and deliveries of the
count's own day are already in it, and only later days are applied (FR-149).

**ASM-072** — A model can pick a useful boost from the facts it is given. This is untested.
Nothing yet measures how his sales respond when the nearby stores run out, so nothing checks
whether a pick was right (§21).

---

### 17. Open Questions

**OQ-901 — RESOLVED (2026-09-25, by the repository owner).** Where do suggestions appear?
On the existing Reorder entry: "don't we have a reorder page, isn't it the same?" Approvals go
to Approved orders, as before, with quantities and no ₪ amounts.

**OQ-902 — RESOLVED (2026-09-25, by the repository owner).** Should a suggestion subtract
recorded stock? Only when the count is at most 7 days old and passes the stock check.
Otherwise show "you'll sell about X before your next order" (FR-149). Today's count is dated
6 June 2026 (`vintages.pos.as_of`), so every suggestion would be gross until a new export
arrives. How the count is carried forward to the order day (FR-149) is this spec's
arithmetic, not part of his answer.

**OQ-903 — Partly resolved (2026-09-25, by the repository owner).** How often does he order?
"Daily and weekly; it depends." The repository owner does not know which departments are
which, and asked that it not be guessed. So the store owner is asked for each department's
schedule (FR-157), and nothing is defaulted (INV-071). The team has added the question to its
owner-conversation list. The values are still open.
· owner: the store owner · blocks: every quantity in a department until its schedule is
recorded

**OQ-904 (P1) — Can his POS export sales and deliveries per product per day, and who sends
it, how often?** PRD §10 already lists the cadence as open. F8 adds the grain (per day,
deliveries included) and a floor on the cadence: at least weekly (FR-144).
· owner: the repository owner, with the store owner · blocks: every quantity (FR-143)

**OQ-905 (P1) — How is "running out" read from three stores of three chains?** This is
GAP-008e. Today's classification tells a stockout from a delisting by how synchronised the
drops are across one chain's 157 branches. The market of D-18 is three stores, each of a
different chain.
· owner: the architect, in V2's design round · blocks: the adjustment and disagreements only
(FR-147, FR-158)

**OQ-906 (P2) — Are the provisional values right?** They are:
- a window of 28 days, holding at least 21 report days with one in each week;
- a freshness limit of 7 days;
- a product counted as moving only if it sold in each of the window's four weeks;
- no quantity below one unit per cycle, and needs rounded to the nearest unit;
- closed days treated as missing days.

· owner: the architect, calibrated with the owner after the first month · blocks: nothing

**OQ-907 — Withdrawn in review (2026-09-25).** It asked whether on-screen order-cycle
questions should come before the cost questions. Order schedules are now gathered by the team
instead (FR-157), so the question no longer arises. The id is not reused.

**OQ-908 — RESOLVED (2026-09-25, by the repository owner).** What does a suggestion do when
the shelf life is unknown? "Ask him first": the store owner states each department's shelf
life in the same conversation as its schedule, and until he has, the department's products
get no quantity (FR-152). The category defaults and an uncapped quantity were the options he
declined.

**OQ-909 — RESOLVED (2026-09-25, by the repository owner).** Should the market boost be one
fixed amount for every product? No: "15% shouldn't be a fixed value". A language model picks
it per product (D-21). He chose this over a boost measured per product, with or without 15%
until then, and over keeping 15% for all, after being told its picks cannot be recomputed or
checked.

**OQ-910 — RESOLVED (2026-09-25, by the repository owner).** What is the most the model may
raise an order by? Up to 25%. A pick above it gives no boost, and the suggestion says it was
rejected (FR-147).

**OQ-911 (P2) — Once his per-day sales overlap enough nearby run-outs to measure a product's
real response, should the measured boost replace the model's pick?** Not needed before then.
· owner: the repository owner · blocks: nothing

---

### 18. Non-Goals

- An order total in ₪, or a supplier purchase order with prices.
- Sending an order anywhere, to a supplier or to his point-of-sale system.
- Ordering by supplier, with supplier lead times or order days (F11).
- On-screen questions about order schedules or shelf life (FR-157).
- Any forecast beyond the daily mean of the recent window: no seasonality, and no weekday
  effects, in this version.
- Rounding to pack or case sizes.
- A sentence explaining a suggestion (F14).
- Acting on disagreement answers (D-20).

---

### 19. Traceability Matrix

| Intent | Requirement | Scenario | Acceptance |
|---|---|---|---|
| INT-004 | FR-143, FR-144 | SCN-132, SCN-144 | AC-136, AC-137, AC-138 |
| INT-004 | FR-145, FR-146 | SCN-133 | AC-139, AC-140 |
| INT-004 (D-18, D-21) | FR-147, FR-148, FR-164 | SCN-136, SCN-137, SCN-150, SCN-151 | AC-141, AC-142, AC-160, AC-161 |
| INT-004 | FR-149, FR-150 | SCN-133, SCN-134, SCN-135, SCN-147 | AC-143, AC-144, AC-157 |
| INT-004 (F10) | FR-151, FR-152 | SCN-138, SCN-139, SCN-146 | AC-145, AC-146 |
| INT-004 | FR-153, FR-154 | SCN-133, SCN-138, SCN-149 | AC-145, AC-148, AC-149, AC-159 |
| INT-004 (D-3) | FR-155, FR-156 | SCN-140, SCN-142, SCN-146, SCN-149 | AC-139, AC-146, AC-147, AC-159 |
| INT-010 | FR-157 | SCN-140 | AC-146, AC-156 |
| INT-004, INT-010 (D-19, D-20) | FR-158, FR-159 | SCN-141, SCN-142, SCN-148 | AC-150, AC-151, AC-155, AC-158 |
| INT-004 | FR-160, FR-161, FR-162, FR-163 | SCN-132, SCN-143, SCN-145 | AC-136, AC-152, AC-153, AC-154 |
| INT-PROV | NFR-066, NFR-067 | — | AC-140, AC-149 |
| INT-010 | NFR-068 | SCN-140 | AC-156 |
| Protected behavior (D-1) | INV-069 | — | AC-148 |
| Protected behavior (rule 13) | INV-070, INV-072 | SCN-132, SCN-144 | AC-137, AC-138, AC-147 |
| Protected behavior (D-3) | INV-071, INV-076 | SCN-140, SCN-146, SCN-149 | AC-139, AC-146, AC-159 |
| Protected behavior | INV-073 | SCN-134, SCN-135, SCN-147 | AC-143, AC-144, AC-157 |
| Protected behavior (D-18, D-21) | INV-074, INV-079, C-71, C-72 | SCN-136, SCN-150 | AC-141, AC-160, AC-161 |
| Protected behavior (D-20) | INV-075, C-67 | SCN-141, SCN-148 | AC-150, AC-151, AC-158 |
| Protected behavior (D-7) | INV-077 | — | AC-153 |
| Protected behavior | INV-078 | SCN-145 | AC-154 |

---

### 20. Boundary Probe

CLAUDE.md rule 12. F8 adds signals, so each input is withheld at source and the published
artefact is read, never a capability's return value. The V1 path exists today (the
engine's inputs → run → publisher). F8's per-day import does not. The implementation plan
names the probe task when it adds that import.

| Probe | What it would catch | Where it runs |
|---|---|---|
| `npm run check:signals`, extended: withhold the report days | The capability claiming `available` with no window, or reading the monthly reports as a substitute | `collect-daily.yml` |
| … withhold the deliveries from the report days | A net quantity computed without them | `collect-daily.yml` |
| … withhold the store facts | Quantities published for departments whose schedule or shelf life is not stated | `collect-daily.yml` |
| … withhold the model | Suggestions vanishing because the boost was wrongly required, or a boost applied from no pick |
| … withhold the market snapshots | Suggestions vanishing because the adjustment was wrongly required, or an adjustment applied from nothing | `collect-daily.yml` |
| … withhold owner state | Disagreements raised again that he already answered | `collect-daily.yml` |
| `scripts/check_independence.py`, extended | The adjustment and the suggestions failing together | `collect-daily.yml` |

---

### 21. Claim Limits

CLAUDE.md rule 13. None of the claims below is "measured and not significant". Each is
**not measurable**, **not measured** or **not known**, and the difference matters.

| Claim | Verdict | Why |
|---|---|---|
| "The market sells a lot of X" | not measurable | Competitor volumes are not observed. Only listings and running out are |
| Weekday or payday patterns in his sales | not measurable from the monthly reports | Rule 13. Measurable once report days exist, but not used in this version |
| Seasonal effects (Ramadan, summer) | not measurable | Seven months, one of each season (PRD §6 #5) |
| That the model's boost is right | not measured | It is a model's estimate (D-21). Nothing yet records how his sales respond when the nearby stores run out, so no pick can be checked (ASM-072) |
| That a quantity prevents a stockout | not measured | Nothing records stockouts at his shop |
| The stock on his shelf right now | not known without report days | The monthly reports record deliveries (receipts on 2,269 of their 3,942 rows), but per month, so they cannot place a delivery before or after a count. Only report days can (FR-149) |
| An order schedule or a shelf life | not inferred at all | Stated by the owner, or measured by F10 (INV-071) |
| Sales in the 17 departments the reports do not itemise | not observed | FR-156 |

**What this spec found cannot honestly produce a quantity today:**
- **The monthly reports.** Dividing them into days or weeks is what Task 0.6 deleted
  `units_sold_30d` for (CLAUDE.md rule 5).
- **A guessed order schedule or shelf life.** OQ-903 and OQ-908 forbid it.
- **The recorded stock.** It is dated 6 June 2026, and 261 of the 1,518 products he sells
  show a negative count (`catalogue.json`).

---

### 22. Unmapped PRD Acceptance Lines

None. The PRD carries no per-feature acceptance table; acceptance is a spec-layer concept in
this project. PRD §5 dates V2 at about 15 October. This spec does not commit to that date,
because F8 cannot publish a quantity before OQ-903, OQ-904 and OQ-908's statements are in.

#### Intent obligations this spec does not satisfy

- **The intent's order, market first and own movement second, is reversed.** D-19 makes his
  own sales set the quantity, and the market only adjusts it. The owner decided this on the
  evidence: competitor volumes are not observable, only running out.
- **"What he could have sold" is not turned into quantities.** The intent says the market
  reveals it. Here it surfaces only as a disagreement question (D-19, D-20).
- **The intent's sentence «هذا الصنف يبيع كثيراً في السوق حولك» is not said.** Competitor
  volumes are not observed, so the question says the stores near him ran out instead (FR-158).
- **The shelf-life cap rests on his statement per department**, not on measurement. F10 is
  not specified.
- **The intent's 527 `WATCH_PRODUCT` products describe nothing now** (GAP-008a).
