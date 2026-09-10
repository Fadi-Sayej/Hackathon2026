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

## The feature list he is shown

One line per feature, one date. No stages, no narrative — that framing was ours, and he does not
buy stages. Names are the PRD §3 feature register in his vocabulary.

| Feature | Register | Date | Bound by |
|---|---|---|---|
| مقارنة أسعارك مع المنافسين | F3 | works now | — |
| كشف فروقات السعر مع Wolt | F1 | works now | — |
| أصناف تُباع تحت التكلفة | SPEC-GAP-A | works now | — |
| تدقيق المخزون والسجلات الخاطئة | F2 | works now | — |
| تسجيل الصلاحية عند الاستلام | — | works now | — |
| شاشة الصباح — 10 إجراءات فقط | F6 | **27/09** | effort — `rankActions` already orders the set |
| تنظيف الكتالوج + ملف للـPOS | F4 | **27/09** | effort — the ghost/idle split already runs |
| أسئلة التكلفة داخل التطبيق | F5 | **27/09** | effort — one missing import path |
| توصيات الطلب — كم تطلب من كل صنف | F8 | **25/10** | **his two-year reports** |
| أصناف يبيعها السوق ولا تبيعها | F9 | **25/10** | effort |
| تتبّع كل رقم — من أين جاء | F7 | **30/10** | effort — the engine rebuild |
| الطلب حسب الصلاحية | F10 | **20/11** | **30 days of receipt logs from 12/09** |
| مهل الموردين الحقيقية | F11 | **20/11** | **3 observed deliveries per supplier** |
| البلانوغرام — ترتيب الرفوف | F12 | **27/11** | shelf photos + F8 + an hour of his rules |

### Two consequences of these dates, recorded rather than hidden

**F8 ships before F7.** Order recommendations land 25/10, five days before the engine that makes
every figure reproducible. So the first ordering recommendations he sees are computed by the
existing pipeline, not by the rebuilt engine — they are honest, but not yet recomputable in
front of him, and the two must agree when F7 lands. If they disagree on 30/10, F7 wins and the
numbers move; say that on the day rather than after.

**Three dates are not ours to hold.** F8 waits on the two-year reports, F10 on thirty days of
receipt logging that starts 12/09, F11 on three deliveries per supplier actually happening. No
amount of engineering compresses any of them, which is why the logging matters from the day of
the meeting and not from the day we need the data.

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
