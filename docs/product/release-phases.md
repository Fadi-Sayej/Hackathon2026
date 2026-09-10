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

## What he is shown: his own ten sentences

The page is the PRD §3 intent table, verbatim, with a date on each line. Nothing else.

| His words (PRD §3, verbatim) | Intent | Date | Bound by |
|---|---|---|---|
| «لا أريد أن أخسر في كل عملية بيع» | INT-001 | works now | — |
| «هل أسعاري معقولة مقابل الجيران؟» | INT-003 | works now | — |
| «أين يختفي مخزوني؟» | INT-002 | works now | — |
| «نظّف كتالوجي من الأصناف الميتة» | INT-009 | **27/09** | effort — the ghost/idle split already runs |
| «أكمل بياناتي الناقصة، بأقل إزعاج» | INT-010 | **27/09** | effort — one missing import path |
| «ماذا أطلب اليوم وبأي كمية؟» | INT-004 | **30/10** | **his two-year reports** |
| «ماذا يبيع السوق ولا أبيعه أنا؟» | INT-005 | **30/10** | effort |
| «كم أطلب حتى لا يتلف؟» | INT-007 | **20/11** | **30 days of receipt logs from 12/09** |
| «متى يصل كل مورّد فعلاً؟» | INT-008 | **20/11** | **3 observed deliveries per supplier** |
| «رتّب رفوفي لأربح أكثر» | INT-006 | **15/12** | shelf photos + INT-004 + an hour of his rules |

### What was taken off the page, and why

Earlier drafts listed data hygiene, the ten-action cap, figure provenance and the cost
questions as features. They are not. They are **how we deliver his ten**, and three of them are
things we need *from* him rather than things he gets:

| Removed | What it actually is |
|---|---|
| «تدقيق المخزون والسجلات الخاطئة» | Part of INT-002. He asked where his stock goes, not for a list of broken records |
| «شاشة الصباح — 10 إجراءات» | INT-NS, our own design rule. He asked for answers, not for a bounded list |
| «تتبّع كل رقم — من أين جاء» | INT-PROV, our rule for keeping ourselves honest. He will use it; he did not ask for it |
| «أسئلة التكلفة داخل التطبيق» | INT-010 is *his* intent — completing his data. The questions are the mechanism, and they are work we ask of him |

The test each line has to pass: **did he say it?** If the sentence is ours, it belongs in this
file, not on his page. INT-NS and INT-PROV are registered as intents in
[the intent register](intent-register.md) precisely because they are cross-cutting rules we
imposed — SPEC-000 §1 says so in as many words.

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
