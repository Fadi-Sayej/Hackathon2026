---
ID: PHASES
Title: Three delivery phases, with dates the customer can hold us to
Status: Proposal — to be confirmed at the 12/9 meeting when capacity is fixed
Version: 1.0 (2026-09-10)
Parent: [PRD](PRD.md) §5 (releases) · §7 (owner commitments) · §8 (decision criterion)
Related: [Implementation plan](../implementation/plan.md) · [System Design](../architecture/system-design.md) §23
---

# Three delivery phases

The customer-facing view of [PRD §5](PRD.md#5-releases-and-dates). Same features, regrouped
into **three things the owner can actually use**, each with a date and each a working product
rather than a milestone.

> **The Arabic page is what he is shown, and it is deliberately thinner than this document.**
> He wants to read a date and a feature name — «23/10: عشرة إجراءات فقط في اليوم» — not our
> reasoning about provenance, availability semantics or capacity arithmetic. All of that stays
> here, where it is for us. The page carries 225 words; this file carries the why behind each
> of them. If the two ever disagree, this one is wrong: he was told the page.

> **This proposes a change to PRD §5's dates and does not take it.** The PRD is the authority
> on when we ship. Its table (V1 ~20/9, V2 ~15/10, V4 ~late October) was assembled on 2026-09-08
> from a note that the code was ready — «الكود جاهز». The System Design's §3 current-state trace,
> written the same day, established that it is not: the engine every V1 figure depends on does
> not exist yet, and §5.4 removes most of what does. PRD §5 already says the capacity figure is
> «رقم مفترض يُثبَّت في اجتماع 12/9» — an assumption to be fixed at the 12/9 meeting, with every
> date moving with it. This is the input to that conversation.

## Why there is a delivery two weeks out

The first version of this plan had him waiting from 12/9 to 23/10 — six weeks — while sending
daily exports, answering twelve questions and having his staff log every delivery. In return,
nothing new. That is not a roadmap, it is a request for patience, and he would have read it
that way.

Three things can ship inside two weeks because the hard part already runs:

| Deliverable | Why it is cheap | Evidence |
|---|---|---|
| The daily list capped at **10** | `rankActions` already orders the whole set; this is a cap and a UI change | `src/lib/analytics/actionPriority.js`, `src/pages/OperationalPage.jsx:157` |
| The **cleanup list** as a CSV he hands to his POS person | The classification already runs — ghost (no sales, zero stock) vs idle (no sales, has stock) | `scripts/print_figures.py:216-233` |
| His **twelve answers actually changing tomorrow's numbers** | `product_recommendations.py` already reads `configs/owner_answers.yaml`; what is missing is the path from the browser into it | `src/lib/questions/answerStore.js:82` exports YAML to **paste by hand**; `scripts/import_owner_answers.py` **does not exist** |

The third is the one that matters most on the day. Asking him for twelve cost answers while the
only way to use them is for one of us to hand-paste a downloaded file is precisely the bargain
he is right to be suspicious of. It is roughly a day of work and it converts the ask into an
exchange.

**The cost, stated honestly:** this is a parallel track on the old pipeline while the engine is
rebuilt, so about 25–30 hours are spent on code that implementation Phase 1 later replaces
(`catalogue_lifecycle` supersedes the CSV, `owner_questions` supersedes the import). That is why
Phase 2 moved from 23/10 to 30/10. Deliberate duplication, bought to remove a six-week silence
in the middle of a pilot whose whole thesis is that he keeps opening the app.

## The arithmetic behind the dates

Two people, **~15 h/week each = 30 h/week combined** (PRD §5's own assumption). The
implementation plan has 37 tasks left across four phases, at roughly 4–5 hours each:

| Work | Tasks | Hours |
|---|---|---|
| Phase 0 foundations, remaining (0.4 … 0.13) | 10 | 40–50 |
| Phase 1 capabilities (1.0 … 1.9) | 10 | 40–50 |
| Phase 2 browser cut-over — **not yet planned** | ~12 | 48–60 |
| Phase 3 reproduction and gates | 5 | 20–25 |
| Visible track shipping 27/9 (above) | — | 25–30 |
| **Total** | **37 +** | **173–215** |

At 30 h/week that is **5.8–7.2 weeks**: 21–31 October. **The dates take the top of that band**,
because a date the customer can hold us to is worth more than an ambitious one we miss. Tasks
0.1–0.3 are done and are not in the count.

**No gap between deliveries now exceeds 33 days**, and the first is 17.

## Phase 1 — «ما يعمل اليوم» · What works today

**Present: 12 September 2026 (the meeting).** Nothing to build. This is the app he already has.

| He can | Today |
|---|---|
| Open one screen each morning and work down a ranked list | **Today** screen |
| See where his shelf price and his own Wolt price disagree | 1,147 flagged products |
| See how his prices sit against Dor Alon, Rami Levy and Shufersal | 1,857 comparisons, each with the date it was seen |
| See products sold below cost | 104 products |
| See records that are simply wrong — negative stock, unknown barcode | 625 + 307 records |
| See stock that cannot reconcile | 458 products |
| Record expiry dates as goods arrive | **Expiry** screen |

Figures are from `public/data/operational.json`, regenerated by CI on 2026-09-10. **Run
`npm run figures` on the morning of the meeting** — the collector runs nightly and a number
written on Thursday is wrong by Saturday (PRD §9).

**What we say plainly, because it is the honest half:** these numbers are not yet reproducible on
demand, and the daily list is not yet capped at ten. Phase 2 is exactly that work.

**What we need from him on the day** — each of these gates something later:

- The daily POS export, and the rhythm agreed (daily or weekly, and who sends it).
- Answers to the **12 cost questions**. Without them 1,270 products stay financially invisible.
- Staff start logging **receipts and expiry that same day** — this starts the 30-day counter and
  is the only source of the shelf-life data Phase 3 needs. It is calendar-bound: no amount of
  engineering shortens it.
- **The two-year sales reports.** Seven months cannot separate seasonal from dead, so until they
  arrive every catalogue withdrawal is labelled provisional.
- The waste baseline — roughly how much he throws away monthly. Without a "before", nothing we
  report at the end can be attributed to us.
- The two numbers of PRD §8: **what ₪ figure after 30 days makes this a success**, and **the
  subscription price if it hits**. Agreed now, not later — a free trial with no agreed price
  measures politeness, not value.

---

## Phase 2 — «كل رقم مسنود» · Every number stands up

**Present: 23 October 2026.** This is PRD V1 (intents 1, 2, 2ب, 3, 9, 10) and implementation
Phases 0–3.

| He gets | Why it matters to him |
|---|---|
| **At most 10 actions a day**, ranked by money, one place per product | Ten minutes means ten minutes. Today's list is 4,498 rows |
| **Every figure recomputable with one command**, in front of him | A number computed while he watches ends an argument; a number quoted off a page starts one |
| **A cleaned catalogue** — 7,674 items down to ~1,535 live, with a CSV for his POS person | We never write to his POS. He hands the list over himself |
| **Cost questions inside the app**, at most 3 at a time, and his answers change the next day's numbers | His knowledge stops being lost |
| **Honest absence** — "unavailable because the sales report did not arrive", never a silent zero | The difference between "nothing to do" and "we could not tell" |
| **His decisions remembered** — Done and Dismiss stick across devices and days | He is not asked the same question twice |

**What moves this date:** the four things that are not code and not ours —
Firebase configured end to end, a read-only service-account secret in CI, Vercel preview
deployments unblocked on account `fadi19`, and the Basic Auth credentials set (unset, the app
answers 503 to everyone). Every one is a prerequisite of implementation Phase 0 and none is on
the critical path *after* it, so they are cheap now and expensive in three weeks.

**Then the clock starts.** 30 days of use → **verdict meeting ~22 November**: the ₪ figure was
reached (subscribe and continue), or it was not but he opens it daily (review the intents with
him), or he does not open it (we stop honourably, having lost a month rather than a year).

> **One thing to settle before this ships:** the 30-day figure does not compute itself. The
> System Design removed the telemetry surface that was assumed to measure it, and nothing has
> been built in its place (ARCH-GATE-003). Either it gets specified before Phase 2 ships, or we
> say so on 12/9 and count it by hand. Not saying anything is the one option that is not available.

---

## Phase 3 — «ماذا أطلب، وكم» · What to order, and how much

**Present: 27 November 2026**, after the verdict meeting. Built during the trial month; shipped
only if Phase 2's verdict says continue. This is PRD V2 (intents 4, 5, 7).

| He gets | Depends on |
|---|---|
| **Order quantities** from market movement and his own sales | The two-year reports, and the sales rhythm holding |
| **What the market sells that he does not** — 527 products observed today | Competitor coverage, which we already collect nightly |
| **Quantities bounded by shelf life** — "order 6, not 12; the rest will spoil" | **30 days of his staff's receipt logs**, starting 12/9. This is why the logging matters from day one |

**What moves this date:** the receipt logs. If logging starts on 12/9 the shelf-life data is
ready around 12/10 and this phase is engineering-bound. If it starts in October, the date moves
by exactly as long as the delay — no engineering can compress it.

---

## After the three phases

- **Planogram — 15 December.** PRD V4. It comes last because it rests on Phase 3's ordering:
  before it, a shelf layout is built on guessed demand and he can tell; after it, the
  justification is "on your own sales" — a number that can be defended. Needs shelf photographs
  with dimensions and an hour of his own arrangement rules. **This is on the page he is shown,
  with a date**, because it is the feature he asks about; the working demo stays hidden until
  the date, because showing it early turns a dated plan back into a promise.
- **Supplier lead times** ship inside Phase 3 once three deliveries per supplier have been
  observed. Calendar-bound, not engineering-bound.
- **Fixed sensors or cameras** are permanently excluded (D-13). Not deferred. If the shelf-photo
  trial succeeds we promise the photo method with confidence; if it fails we know *before*
  promising.

## The rule under all three dates

Every one assumes 30 h/week combined. The first thing to fix on 12/9 is whether that number is
real. If it is 20, every date after Phase 1 moves out by two to three weeks, and the customer
hears that on 12/9 rather than on 23/10.
