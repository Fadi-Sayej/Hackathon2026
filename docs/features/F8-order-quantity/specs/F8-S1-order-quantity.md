---
ID: F8-S1
Title: Order Quantity — what to order, and how much, for the next order
Status: Ready for review
Owner: smartshelf-architect
Version: 0.1 (2026-09-25)
Parent: [F8 — Order Quantity](../intent.md)
Related Intents: INT-004, INT-010
Inputs: [docs/features/F8-order-quantity/intent.md, docs/product/PRD.md §5 §6 §7 §10, docs/product/intent-register.md (D-1, D-3, D-7, D-8, D-10, D-18, D-19, D-20), docs/features/gaps-and-open-questions.md (GAP-008, GAP-009), docs/pilot/owner-conversation-2026-09.md, F2-S1, F5-S1, F7-S1, F10 intent, ADR-001, ADR-002, ADR-003, ADR-004, ADR-005, ADR-007, ADR-008, ADR-009, ADR-011, ADR-012, ADR-014, ADR-016, ADR-017, ADR-024, ADR-027, ADR-028, CLAUDE.md, public/data/dashboard.json and catalogue.json (generated 2026-09-24T02:46Z), data/internal/silver_pos/*.parquet]
Answered by: [System Design](../../../architecture/system-design.md) §21 — a placeholder until V2's first design round
Updated: 2026-09-25
---

# F8-S1 — Order Quantity

> **The first V2 spec, and what it rests on.** It turns D-18 … D-20 into requirements, and
> the three answers the repository owner gave on 2026-09-25 (§17, OQ-901 … OQ-903). It can
> be reviewed and designed now. **It cannot publish a single quantity until two inputs exist
> that do not exist today:**
> - sales reported **per day, or per week**;
> - each department's **order cycle**, stated by the store owner.
>
> Until then the Reorder entry keeps saying what it waits for (FR-160). That is deliberate.
> Every shorter path found while writing this spec needed a number nobody has: a daily rate
> divided out of a monthly report, a guessed order cycle, a stock count from June (§21).

Implements intent F8. Bound by ADR-001, ADR-003, ADR-005, ADR-007, ADR-008, ADR-009,
ADR-011, ADR-012, ADR-014, ADR-016, ADR-027 and ADR-028, and by settled decisions D-1, D-3,
D-7, D-8, D-10, D-18, D-19 and D-20.

---

### 1. Purpose

Tells the owner, product by product, how many to order for his next order. The quantity is:
- **set by his own sales** (D-19);
- **raised by one fixed, stated amount** when the stores near him run out (D-18, D-19);
- **capped** by what sells before it spoils (F10);
- **reduced by his stock** only when the count is recent and checks out (OQ-902).

Where the evidence cannot support a number, it shows none (D-3). Where only he holds the
missing fact, it asks him (F5). It never writes to his point-of-sale system (D-7), never
puts a ₪ figure on a suggestion (D-1), and never fills an unknown with a guess: not an
order cycle, not a shelf life, not a missing day's sales.

---

### 2. Intent Traceability

| Intent | This spec |
|---|---|
| INT-004 — «ماذا أطلب اليوم وبأي كمية؟» | FR-143 … FR-163 |
| INT-010 — "Complete my missing data — with minimum disturbance" | FR-157 … FR-159. The facts F8 needs from him are asked under F5-S1's rules |
| INT-PROV — every figure recomputable | FR-154. F7-S1 governs every figure here in full |

It also serves:
- **PRD §5:** V2, «الطلب من السوق».
- **PRD §6 #3:** V2 "recommends confidently on what moves, and stays silent about the long
  tail rather than guessing" (FR-145, FR-155).
- **PRD §7:** the POS export commitment, which F8 depends on (OQ-904).

---

### 3. Scope

#### In Scope

- A quantity per product for the next order of its department, for products with enough
  of his own sales (D-19).
- The market adjustment: one fixed, stated rise when the market of D-18 runs out of the
  product (D-19).
- Subtracting his recorded stock, only when the count is recent and checks out (OQ-902).
- A shelf-life cap, from a shelf life measured by F10 or stated by the owner.
- The questions F8 needs answered:
  - each department's order cycle and shelf life;
  - the disagreement between the market and his own sales (D-19, D-20).
- The existing Reorder and Approved orders entries (OQ-901): suggestions, approve, change or
  dismiss, and a list of approved lines he can export.

#### Out of Scope

- Writing anything to his point-of-sale system (D-7).
- Any ₪ figure on a suggestion or on an approved line, totals included (D-1, ADR-012).
- Supplier grouping, supplier lead times and supplier order days. No supplier is recorded
  for any product he sells, and lead times are F11 (V3).
- Measuring shelf life. That is F10.
- The reason written as a sentence. That is F14 (D-15, D-16); F8 publishes the facts it
  will be written from.
- Letting a disagreement answer change a quantity. D-20 leaves that for later.
- What the market sells that he does not. That is F9 (INT-005), whose own decision stays
  open.
- Seasonal forecasting (PRD §6 #5), and pack or case sizes, which are not recorded.

---

### 4. Actors and Triggers

| Actor | Trigger | Frequency |
|---|---|---|
| Engine | The nightly run publishes suggestions from the inputs that landed | Nightly (ADR-007) |
| Store owner | Opens Reorder; approves, changes or dismisses suggestions | When he orders: daily or weekly, depending on the department (OQ-903) |
| Store owner | Answers a question F8 raised | When presented, at most three at a time (D-8) |
| Team or store owner | Delivers the POS sales export | Per the owner commitment (PRD §7). Its cadence is open (PRD §10, OQ-904) |

---

### 5. Domain Terms

| Term | Definition |
|---|---|
| **Order cycle** | The number of whole days between two orders of a department's products, as the store owner states it. Never inferred and never defaulted (OQ-903) |
| **Report period** | The span one row of sales evidence covers: a day, a week or a calendar month |
| **Fitting period** | A report period that goes into the order cycle a whole number of times. A day fits every cycle. A week fits a cycle of whole weeks. A calendar month fits only a cycle stated in months |
| **Cycle window** | The N most recent complete order cycles of fitting periods (FR-144) |
| **Moving product** | One that sold in every cycle of its window (FR-145) |
| **Expected sales** | The units sold in the window divided by N: the average per order cycle (FR-146) |
| **The market** | The nearby stores at or above the format floor (D-18). Three today |
| **Running out** | The market's stockout classification for a product (FR-147, OQ-905) |
| **Usable count** | A recorded stock count at most 7 days older than the run, not negative, and flagged by neither reconciliation nor hygiene (FR-149) |
| **Gross quantity** | What he is expected to sell before his next order |
| **Net quantity** | The gross quantity less a usable count, never below zero |
| **Disagreement** | The market running out of a product in his catalogue that is not moving, in a department whose order cycle is known (FR-158) |
| **Suggestion** | One product's quantity for an order placed on the run's date, with the facts it was computed from |

---

### 6. Functional Requirements

#### Evidence

**FR-143** — Quantities are computed only from sales reported in periods that fit the
department's order cycle. A report period is never divided into shorter ones. So the seven
monthly reports, today's only sales evidence, cannot supply a quantity for any cycle shorter
than a month (CLAUDE.md rule 13; ADR-028 §4).

**FR-144** — A product's cycle window is its N most recent complete cycles, none ending more
than 2N cycles before the run. A cycle is complete when every one of its fitting periods was
reported. A period with no report is missing; it is not a period of zero sales. N is a
policy value, provisionally 4 (OQ-906).

**FR-145** — A product is moving when it sold in every cycle of its window. Only a moving
product gets a quantity (D-19; PRD §6 #3).

**FR-146** — A moving product's expected sales are the units it sold in its window, divided
by N.

#### The market adjustment

**FR-147** — When the market (D-18) is running out of a moving product, its expected sales
are raised by the stated lift, once. The lift is 15% today (D-19). A store below the format
floor never triggers it, and neither does the national price file (D-18).

**FR-148** — The market adjustment can become unavailable on its own (ADR-014). When the
running-out signal cannot be computed, suggestions are still published, unadjusted, and
each says that the market signal was unavailable and why.

#### Stock

**FR-149** — A recorded stock count is subtracted only when it is usable:
- at most 7 days older than the run;
- not negative;
- flagged by neither reconciliation nor hygiene (F2-S1).

With a usable count the suggestion is net. Otherwise it is gross, shows the count with its
date, and says why the count was not used (OQ-902).

**FR-150** — A product whose net quantity is zero is not suggested. The Reorder entry states
how many moving products the recorded stock already covers.

#### Shelf life

**FR-151** — Where a product's shelf life is known, its quantity is at most what sells
within it. A shelf life is known when F10 measured it or the owner stated it for the
product's department. The cap is the product's mean units per fitting period, multiplied by
the whole number of fitting periods the shelf life spans. A shelf life shorter than one
fitting period yields no quantity, and the suggestion says why.

**FR-152** — Where the shelf life is unknown, the quantity is published without a cap and
says so. No shelf life is defaulted. The category table of starting guesses is not an input
to F8.

#### The quantity

**FR-153** — A suggestion's quantity is the lesser of the need and the shelf-life cap
(FR-151), in the unit the sales report counts. The need is the gross quantity (FR-146,
FR-147), less a usable count (FR-149). A need is rounded up to a whole unit. A quantity the
cap sets is rounded down, so rounding never orders past what sells before it spoils; a cap
that rounds down to zero yields no quantity, and says why. It carries no ₪ figure (D-1).

**FR-154** — Every suggestion publishes the facts it was computed from:
- the order cycle;
- the window's dates, and each cycle's units;
- the expected sales;
- whether the market adjustment applied, and why not if it did not;
- the recorded count, its date, and whether it was used, with the reason;
- the shelf life, its source, and whether it capped the quantity;
- whether the quantity is net or gross.

Each is recomputable (F7-S1). These are the facts F14 will explain (D-16).

#### No quantity

**FR-155** — A product gets no quantity, meaning not a zero and not a small number, when:
- it is not moving;
- its department's order cycle is unknown;
- no fitting sales evidence exists for its department;
- its shelf life is shorter than one fitting period.

The Reorder entry says, per department, which of these holds (D-3).

**FR-156** — A department with no sales row at all in the evidence is treated as not
covered by the evidence. It is never read as a department that sold nothing. Its products
get no quantity and raise no disagreement, and the Reorder entry says the sales evidence
does not itemise the department. Today 17 of the catalogue's 55 departments, holding 225
products, have no row in any of the seven monthly reports; five of them hold 25 to 46
products each (GAP-009).

#### Questions

**FR-157** — The facts F8 needs, which only the owner holds, are asked under F5-S1's rules:
at most three questions at once (D-8); an answered question is not asked again (FR-089); a
deferral is not an answer (FR-091). F8 asks for:
- **a department's order cycle**, while it is unknown and the department appears in the
  sales evidence. The answer changes output as soon as it does: a cycle stated in months
  can draw on the monthly reports today (FR-143);
- **a department's shelf life**, while it is unknown and the department has a suggestion.

Neither is ever defaulted, inferred, or taken from the category table (OQ-903).

**FR-158** — A disagreement raises one question for the product instead of a quantity
(D-19, D-20). It arises only in a department whose order cycle is known, since "not moving"
is measured over the cycle window. The question states only what was observed:
- that the stores near him ran out of the product;
- what he sold in the window, or that he sold none.

It then asks why: the product's place on the shelf, its price, or a weak market for it here
(intent §6). It never claims the market sells a lot of the product, because competitor
volumes are not observed (§21).

**FR-159** — His answer is saved in owner state (ADR-003) and retires that product's
disagreement. It is not raised again, even when the facts later change (D-20). The answer
changes no quantity (D-20). He can still revise it (F5-S1 FR-090).

#### Reorder and Approved orders

**FR-160** — Suggestions appear on the existing Reorder entry (ADR-028 §1), grouped by
department. While F8 cannot publish, the entry keeps saying what it waits for, and names the
missing input (OQ-901).

**FR-161** — For each suggestion he can approve it as suggested, approve it with his own
quantity, or dismiss it.
- His quantity is authoritative (F5-S1 FR-087), and is recorded beside the suggested one.
- Outcomes are owner state (ADR-003), keyed on an entry id that is stable for that product
  and order date (ADR-009).
- The outcome snapshot carries its signal family (ADR-016).

**FR-162** — Approved lines appear on the existing Approved orders entry, grouped by
department. Each shows the product, the quantity and the order date; there is no unit cost,
subtotal or total (D-1, ADR-012). He can export the lines as a CSV to give his suppliers.
Nothing is written to his point-of-sale system (D-7).

**FR-163** — A suggestion belongs to one order date. The next cycle's suggestion for the
same product is a new entry; an approval or a dismissal does not carry over to it.

---

### 7. Behavioral Invariants

**INV-069** — No suggestion, approved line or export carries a ₪ figure, and no total of any
kind is shown (D-1, ADR-012). A violation would read: "estimated order total ₪…" on Approved
orders.

**INV-070** — No quantity is derived by dividing a report period into shorter ones. A
violation would read: a weekly quantity equal to a month's units divided by 4.3.

**INV-071** — No order cycle or shelf life is defaulted, inferred from a category table, or
copied from another department. An unknown fact yields no quantity or no cap, and the
suggestion says so (D-3).

**INV-072** — A period with no report is never read as zero sales. A department with no row
in the evidence is never read as one that sold nothing (ADR-011).

**INV-073** — A recorded count that is not usable is never subtracted (FR-149).

**INV-074** — The market adjustment is applied at most once per suggestion, by exactly the
stated lift, and only from the market of D-18.

**INV-075** — A disagreement is raised at most once per product. Once answered it is never
raised again, and its answer never changes a quantity (D-20).

**INV-076** — A product that is not moving never receives a quantity, whether zero or small
(D-19, D-3).

**INV-077** — Nothing F8 does writes to the owner's point-of-sale system (D-7).

---

### 8. Behavioral Scenarios

**SCN-132 — Only the monthly reports**
GIVEN the only sales evidence is the seven monthly reports
WHEN the engine runs
THEN no quantity is published for any cycle shorter than a month, and Reorder says it waits for sales reported per day or per week.

**SCN-133 — A gross suggestion**
GIVEN per-day reports for the last four weeks, a department stated as weekly, a product sold in each of those weeks, no market signal, and a recorded count from 6 June
WHEN the engine runs
THEN the suggestion is the four-week average, gross, and says the count was not used because it is older than 7 days.

**SCN-134 — A net suggestion**
GIVEN the same, with a count taken three days before the run that neither reconciliation nor hygiene flags
WHEN the engine runs
THEN the suggestion is the average less the count, and says so.

**SCN-135 — A flagged count**
GIVEN a recent count for a product that reconciliation flags
WHEN the engine runs
THEN the suggestion is gross, and names the flag as the reason the count was not used.

**SCN-136 — The market runs out**
GIVEN the market's signal says it is running out of a moving product
WHEN the engine runs
THEN expected sales are raised by the stated 15%, once, and the suggestion says so.

**SCN-137 — Market signal unavailable**
GIVEN the nearby stores' snapshots cannot be read
WHEN the engine runs
THEN suggestions are published unadjusted, each saying the market signal was unavailable, and no disagreement is raised.

**SCN-138 — Shelf life caps the quantity**
GIVEN a department stated as weekly, a product whose shelf life is 2 days, and per-day reports
WHEN the engine runs
THEN its quantity is at most two days' average sales, and the suggestion says it was capped.

**SCN-139 — Shelf life shorter than the report period**
GIVEN per-week reports only, and a product whose shelf life is 2 days
WHEN the engine runs
THEN no quantity is published, and the suggestion says the reports are coarser than its shelf life.

**SCN-140 — Order cycle unknown**
GIVEN a department whose order cycle has not been stated
WHEN the engine runs
THEN its products get no quantity, Reorder says the cycle is missing, and a question asking for it becomes eligible.

**SCN-141 — Disagreement**
GIVEN the market is running out of a product he sold in only one of its four cycles
WHEN the engine runs
THEN no quantity is published and one question is raised, stating what was observed. Once he answers, it is never raised again and no quantity changes.

**SCN-142 — A department the reports do not itemise**
GIVEN a department with no row in any sales report, and the market running out of one of its products
WHEN the engine runs
THEN its products get no quantity, no disagreement is raised, and Reorder says the evidence does not itemise the department.

**SCN-143 — Approve with his own quantity**
GIVEN a suggestion of 12
WHEN he approves it with 20
THEN Approved orders lists 20 for that order date, the suggested 12 is recorded beside it, and the next cycle's suggestion is a new entry.

**SCN-144 — A missing day**
GIVEN one day's report is missing inside the latest cycle
WHEN the engine runs
THEN that cycle is incomplete, and the window uses the four most recent complete cycles if they lie within eight cycles; otherwise no quantity is published, and the suggestion says a report is missing.

---

### 9. Inputs and Observable Outputs

| Input | Source | Required? |
|---|---|---|
| Sales per product per day, or per week | The POS sales export (PRD §7; OQ-904), a new import. The monthly reports are not a substitute (FR-143) | Yes. Without it, no quantity |
| Each department's order cycle | The store owner, as owner state (FR-157) | Yes, per department |
| Recorded stock and its date | The POS export, as F2-S1 reads it | No. Without a usable count, the suggestion is gross |
| Reconciliation and hygiene flags | F2-S1 | No. Needed only to use a count |
| The market's running-out signal | The daily delivery snapshots of the D-18 stores (OQ-905) | No. Without it, no adjustment and no disagreement |
| The lift | The configured `stockout_demand_lift`, 1.15 today | Yes, when the signal applies |
| Shelf life | F10, or the store owner per department | No. Without it, no cap |
| Catalogue membership and department | The published catalogue (ADR-024) | Yes |
| His answers and outcomes | Owner state (ADR-003) | No |

| Output | Where it is observable |
|---|---|
| Suggestions with their facts, and per-department reasons for no quantity | The artefact; the Reorder entry |
| Questions | F5's question panel |
| Approved lines | The Approved orders entry, and its CSV export |

---

### 10. State / Lifecycle Semantics

The engine recomputes suggestions every run and stores none of them (ADR-004). What
persists is the owner's: his outcomes, cycles, shelf lives and answers, in owner state
(ADR-003).

| Thing | Transitions | Persists? |
|---|---|---|
| Suggestion | published → approved (as suggested, or with his quantity) or dismissed | The outcome does, keyed on product and order date. It does not carry to the next cycle (FR-163) |
| Order cycle, shelf life | unknown → stated → revised | Yes. Revisable (F5-S1 FR-090), never overwritten by inference (FR-087) |
| Disagreement | raised → answered → retired | Yes. Never reopened (D-20) |

---

### 11. Failure and Recovery Behavior

| Condition | Required behavior |
|---|---|
| No sales at a fitting grain | The capability is unavailable and names the missing input; Reorder says what it waits for (FR-160). An empty list is a failure, not a result (CLAUDE.md rule 10) |
| Some export days missing | The window skips incomplete cycles, within 2N (FR-144). Beyond that there is no quantity, and the suggestion names the missing report |
| A department's order cycle unknown | No quantity for that department; its question becomes eligible (FR-157) |
| Market snapshots missing or unclassifiable | The adjustment becomes unavailable on its own; suggestions still publish (FR-148) |
| Owner state unreachable | As ADR-003 and ADR-017 define: the run is degraded, and the cycles it uses are those of the last owner state it holds, stated with that state's date |
| Recorded count missing, or its date unknown | Not usable: the suggestion is gross (FR-149) |
| A report period that does not fit the cycle | Not used for that cycle. Never divided (FR-143) |

---

### 12. Edge Cases

| Case | Behaviour |
|---|---|
| A department he orders monthly | The monthly reports fit it (FR-143), so its products can get quantities from them |
| An irregular cycle, three days then four | The cycle is what he states. F8 does not average two cycles into 3.5 days |
| Goods sold by weight | The quantity is in the report's unit, rounded to a whole unit of it (FR-153) |
| Less than one unit sells within the shelf life | No quantity: the cap rounds down to zero (FR-153) |
| A product F4 withdrew | Not moving, so not suggested and not asked about (F5-S1 FR-082) |
| Net quantity of zero | Not suggested; counted as covered by stock (FR-150) |
| He changes a department's cycle | The next run uses the new cycle. Earlier outcomes keep their order dates |
| A disagreement product that later starts moving | It gets a quantity. If he already answered, the disagreement stays retired |

---

### 13. Non-Functional Requirements

**NFR-066 (Determinism)** — The same inputs, policy and owner state produce the same
suggestions, questions and facts.

**NFR-067 (Recomputability)** — Every quantity is reproducible from its published facts by
the engine in print mode (ADR-002, F7-S1).

**NFR-068 (Owner effort)** — F8's questions are bounded by suppression, not only by the
limit (F5-S1 NFR-040). A department is asked about only while its answer would change a
published output.

**NFR-069 (No runtime)** — Suggestions are computed in the nightly run. The page computes
nothing (ADR-001, ADR-007).

---

### 14. Compatibility and External Constraints

**C-63** — ADR-001: the engine computes every quantity. The browser renders suggestions and
records his outcomes.

**C-64** — ADR-005 and ADR-014: F8 publishes through the capability contract, and the market
adjustment is a separately-unavailable unit.

**C-65** — ADR-003: his answers and outcomes are owner state. The browser writes them and
the engine pulls them; the engine never writes them back.

**C-66** — ADR-008 and D-18: only stores at or above the floor may move a quantity. Below
it, a store is context only (F3-S1 C-21).

**C-67** — F5-S1: F8's questions obey FR-084 … FR-091, with two points of contact:
- FR-080 requires an answer to change an output. A disagreement answer does: it retires the
  disagreement.
- FR-089's re-ask on a changed fact does not apply to disagreement answers, because D-20
  prevails.

**C-68** — ADR-027: F8's questions carry no ₪ figure, so they are ordered after every
question that has one. Today that means after all 11 open questions in the artefact, each
of which has a figure (OQ-907).

**C-69** — ADR-011: a missing report or a missing row is stated as such ("no sales row"),
never as "zero sales".

**C-70** — ADR-028: F8 lights the existing Reorder and Approved orders entries, and does so
on real per-day demand, not on the monthly reports (§4).

---

### 15. Acceptance Criteria

**AC-136** — With only the monthly reports, no quantity is published for any cycle shorter
than a month, and Reorder names the missing input. *(FR-143, FR-160, INV-070, SCN-132)*

**AC-137** — No quantity equals a report period's units divided into a shorter period.
*(FR-143, INV-070)*

**AC-138** — A cycle with a missing report never counts as a cycle of zero sales, and the
window uses complete cycles only. *(FR-144, INV-072, SCN-144)*

**AC-139** — A product that did not sell in every cycle of its window has no quantity, not
a zero. *(FR-145, FR-155, INV-076)*

**AC-140** — Expected sales equal the window's units divided by N, reproducible from the
published facts. *(FR-146, FR-154, NFR-067)*

**AC-141** — When the market is running out, the quantity is raised by exactly the stated
lift, once, and says so. A store below the floor never raises it. *(FR-147, INV-074,
SCN-136)*

**AC-142** — With the market signal withheld, suggestions still publish, unadjusted, each
saying why, and no disagreement is raised. *(FR-148, SCN-137)*

**AC-143** — A count older than 7 days, negative, or flagged by reconciliation or hygiene is
never subtracted, and the suggestion says which. *(FR-149, INV-073, SCN-133, SCN-135)*

**AC-144** — With a usable count, the suggestion is the gross quantity less the count, never
below zero. A zero is not suggested, and is counted as covered. *(FR-149, FR-150, SCN-134)*

**AC-145** — A known shelf life caps the quantity at whole fitting periods. One shorter than
a fitting period yields no quantity. *(FR-151, SCN-138, SCN-139)*

**AC-146** — No shelf life or order cycle is defaulted. An unknown one yields no cap or no
quantity, and says so. *(FR-152, FR-155, INV-071, SCN-140)*

**AC-147** — A department with no row in the evidence gets no quantity and raises no
disagreement. *(FR-156, INV-072, SCN-142)*

**AC-148** — No suggestion, approved line or export carries a ₪ figure or a total.
*(FR-153, FR-162, INV-069)*

**AC-149** — Every suggestion publishes the facts of FR-154, each recomputable. *(FR-154,
NFR-066, NFR-067)*

**AC-150** — F8's questions never make more than three on screen at once, counting every
other question, and are ordered after every question with a ₪ figure. *(FR-157, C-67, C-68)*

**AC-151** — A disagreement question states only what was observed and is raised once per
product. Once answered, it is never raised again and changes no quantity. *(FR-158, FR-159,
INV-075, SCN-141)*

**AC-152** — Approving with his own quantity lists his quantity on Approved orders, with
the suggested one recorded. The next cycle's suggestion is a new entry. *(FR-161, FR-162,
FR-163, SCN-143)*

**AC-153** — The Approved orders export holds the product, barcode, quantity and order date,
and nothing is written to the point-of-sale system. *(FR-162, INV-077)*

---

### 16. Assumptions

**ASM-064** — His POS can export sales per product per day, or per week. Unverified. If it
cannot, F8 can serve only departments ordered monthly (FR-143). *(OQ-904)*

**ASM-065** — Within a department the report itemises, a product absent from a day's report
sold nothing that day. This is GAP-009's reading. FR-156 confines it to departments that
appear in the evidence at all, and it is to be confirmed with the owner for the daily
reports before release.

**ASM-066** — His order rhythm follows the department. No supplier is recorded for any of
the 1,518 products he sells (yomyom_products.parquet). If his rhythm follows the supplier
instead, the grouping changes once suppliers are recorded.

**ASM-067** — Recent sales predict the next cycle. Nothing seasonal is measurable from seven
months (PRD §6 #5). Ramadan and the summer peaks can falsify this, which is why the window's
dates are published, so the age of the evidence is visible.

**ASM-068** — The units he orders are the units the report counts. Pack and case sizes are
not recorded.

---

### 17. Open Questions

**OQ-901 — RESOLVED (2026-09-25, by the repository owner).** Where do suggestions appear?
On the existing Reorder entry: "don't we have a reorder page, isn't it the same?" Approvals go
to Approved orders, as before, with quantities and no ₪ amounts.

**OQ-902 — RESOLVED (2026-09-25, by the repository owner).** Should a suggestion subtract
recorded stock? Only when the count is at most 7 days old and passes the stock check
(FR-149). Today's count is dated 6 June 2026 (`vintages.pos.as_of`), so every suggestion
would be gross until a new export arrives.

**OQ-903 — Partly resolved (2026-09-25, by the repository owner).** How often does he order?
"Daily and weekly; it depends." The repository owner does not know which departments are
which, and asked that it not be guessed. So the store owner is asked, per department
(FR-157), and the cycle is never defaulted (INV-071). The values are still open.
· owner: the store owner · blocks: every quantity in a department until its cycle is stated

**OQ-904 (P1) — Can his POS export sales per day, how often will it be sent, and by whom?**
PRD §10 already lists the cadence as open, and the owner conversation asks it (question 6).
F8 adds the grain: per day, or at least per week.
· owner: the repository owner, with the store owner · blocks: every quantity (FR-143)

**OQ-905 (P1) — How is "running out" read from three stores of three chains?** This is
GAP-008e. Today's classification tells a stockout from a delisting by how synchronised the
drops are across one chain's 157 branches. The market of D-18 is three stores, each of a
different chain.
· owner: the architect, in V2's design round · blocks: the adjustment and disagreements only
(FR-147, FR-158)

**OQ-906 (P2) — Is the provisional rule right: a window of four cycles, and a product
counted as moving only if it sold in every one?** A daily cycle then needs four days of
evidence, a weekly one four weeks.
· owner: the architect, calibrated with the owner after the first month · blocks: nothing

**OQ-907 (P2) — Should order-cycle questions come before the cost questions?** Under ADR-027
they follow every question with a ₪ figure. And F8 shows no quantity in a department until
its cycle is answered.
· owner: the repository owner · blocks: how soon F8 is useful, not whether it is correct

---

### 18. Non-Goals

- An order total in ₪, or a supplier purchase order with prices.
- Sending an order anywhere, to a supplier or to his point-of-sale system.
- Ordering by supplier, with lead times or order days (F11).
- Any forecast beyond the average of recent cycles: no seasonality, and no weekday effects,
  in this version.
- Rounding to pack or case sizes.
- A sentence explaining a suggestion (F14).
- Acting on disagreement answers (D-20).

---

### 19. Traceability Matrix

| Intent | Requirement | Scenario | Acceptance |
|---|---|---|---|
| INT-004 | FR-143, FR-144 | SCN-132, SCN-144 | AC-136, AC-137, AC-138 |
| INT-004 | FR-145, FR-146 | SCN-133 | AC-139, AC-140 |
| INT-004 (D-18, D-19) | FR-147, FR-148 | SCN-136, SCN-137 | AC-141, AC-142 |
| INT-004 | FR-149, FR-150 | SCN-133, SCN-134, SCN-135 | AC-143, AC-144 |
| INT-004 (F10) | FR-151, FR-152 | SCN-138, SCN-139 | AC-145, AC-146 |
| INT-004 | FR-153, FR-154 | SCN-133 | AC-148, AC-149 |
| INT-004 (D-3) | FR-155, FR-156 | SCN-140, SCN-142 | AC-139, AC-146, AC-147 |
| INT-010 (D-8) | FR-157 | SCN-140 | AC-150 |
| INT-004, INT-010 (D-19, D-20) | FR-158, FR-159 | SCN-141 | AC-151 |
| INT-004 | FR-160, FR-161, FR-162, FR-163 | SCN-132, SCN-143 | AC-136, AC-152, AC-153 |
| INT-PROV | NFR-066, NFR-067 | — | AC-140, AC-149 |
| Protected behavior (D-1) | INV-069 | — | AC-148 |
| Protected behavior (rule 13) | INV-070, INV-072 | SCN-132, SCN-144 | AC-137, AC-138, AC-147 |
| Protected behavior (D-3) | INV-071, INV-076 | SCN-140 | AC-139, AC-146 |
| Protected behavior | INV-073 | SCN-135 | AC-143 |
| Protected behavior (D-18) | INV-074 | SCN-136 | AC-141 |
| Protected behavior (D-20) | INV-075 | SCN-141 | AC-151 |
| Protected behavior (D-7) | INV-077 | — | AC-153 |

---

### 20. Boundary Probe

CLAUDE.md rule 12. F8 adds signals, so each input is withheld at source and the published
artefact is read, never a capability's return value. The V1 path exists today (the
engine's inputs → run → publisher). F8's per-day sales import does not. The implementation
plan names the probe task when it adds that import.

| Probe | What it would catch | Where it runs |
|---|---|---|
| `npm run check:signals`, extended: withhold the per-day sales | The capability claiming `available` with no fitting evidence, or reading the monthly reports as a substitute | `collect-daily.yml` |
| … withhold the market snapshots | Suggestions vanishing because the adjustment was wrongly required, or an adjustment applied from nothing | `collect-daily.yml` |
| … withhold owner state | Quantities published for departments whose cycle is unknown | `collect-daily.yml` |
| `scripts/check_independence.py`, extended | The adjustment and the suggestions failing together | `collect-daily.yml` |

---

### 21. Claim Limits

CLAUDE.md rule 13. None of the claims below is "measured and not significant". Each is
**not measurable** or **not measured**, and the difference matters.

| Claim | Verdict | Why |
|---|---|---|
| "The market sells a lot of X" | not measurable | Competitor volumes are not observed. Only listings and running out are |
| Weekday or payday patterns in his sales | not measurable from the monthly reports | Rule 13. Measurable once per-day sales exist, but not used in this version |
| Seasonal effects (Ramadan, summer) | not measurable | Seven months, one of each season (PRD §6 #5) |
| That a 15% raise is right | not measured | The configuration calls it a starting figure. No stockout has yet been observed alongside his till data |
| That a quantity prevents a stockout | not measured | Nothing records stockouts at his shop |
| An order cycle or a shelf life | not inferred at all | Stated by the owner, or measured by F10 (INV-071) |
| Sales in the 17 departments the reports do not itemise | not observed | FR-156 |

**What this spec found cannot honestly produce a quantity today:**
- **The monthly reports.** Dividing them into days or weeks is what Task 0.6 deleted
  `units_sold_30d` for (CLAUDE.md rule 5).
- **A guessed order cycle.** OQ-903 forbids it.
- **The recorded stock.** It is dated 6 June 2026, and 261 of the 1,518 products he sells
  show a negative count (`catalogue.json`).

---

### 22. Unmapped PRD Acceptance Lines

None. The PRD carries no per-feature acceptance table; acceptance is a spec-layer concept in
this project. PRD §5 dates V2 at about 15 October. This spec does not commit to that date,
because F8 cannot publish a quantity before OQ-903 and OQ-904 are answered.

#### Intent obligations this spec does not satisfy

- **The intent's order, market first and own movement second, is reversed.** D-19 makes his
  own sales set the quantity, and the market only adjusts it. The owner decided this on the
  evidence: competitor volumes are not observable, only running out.
- **"What he could have sold" is not turned into quantities.** The intent says the market
  reveals it. Here it surfaces only as a disagreement question (D-19, D-20).
- **The shelf-life cap is partial.** It applies only where a shelf life is known. F10 is not
  specified.
- **The intent's 527 `WATCH_PRODUCT` products describe nothing now** (GAP-008a).
