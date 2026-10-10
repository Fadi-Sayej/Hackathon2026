---
ID: F14-S1-SCREENS-MOCKUPS
Title: The AI's explanation on every order suggestion (D-40) — mockups for the repository owner's approval
Status: Approved — by the repository owner, 2026-10-10 ("it is good merge and push")
Owner: smartshelf-engineer
Parent: [F14-S1](../features/F14-decision-explanations/specs/F14-S1-decision-explanations.md) v0.1 at b4a1285 (Ready for review, branch `docs/f14-spec`), C-79, OQ-1403
Inputs: [D-29, D-40, F14-S1 FR-238, FR-242, FR-243, FR-244, Appendix A, docs/reviews/F8-screens-mockups.md, docs/reviews/F12-screens-mockups.md]
Updated: 2026-10-10
---

# The AI's explanation on each Reorder card — mockups for approval

> **Approved by the repository owner on 2026-10-10** ("it is good merge and push"), after seeing
> the redraw on F14-S1's final phrases: the card, the note and the phrases as drawn. He asked why
> the same figure appears several times on the במבה and ביסלי גריל cards. The answer was the test
> shop: it sells the same amount every day, so each week's figure, the expected sales and the
> order collapse into one number. He kept the drawing as it is. The engine half, `order_explanation`,
> is not built yet, so nothing on the owner's screens changes until it publishes.

D-40 (2026-10-09): every order suggestion carries the AI's explanation of why that quantity. These
are the Reorder screens that F14-S1 proposes for it, their words in the three languages, and what
you are asked to decide. Nothing here is merged or shown to a store until you approve it.

**How they were made.** They were drawn inside the real app, in the e2e build, at phone size
(390 × 844). The code is on the branch `ui/f14-mockups`, which is not merged. In these pictures:
- **the shop is Reorder's marked example** (D-29), the test shop, not any store's data;
- **every explanation is HAND-WRITTEN SAMPLE WORDING, not the model's.** The model has never been
  asked: no store sends daily sales (D-23), and the model key is not set up. Each sample was written
  around the slots only, and each passes F14-S1's mechanical check as the spec states it at b4a1285
  (FR-238, Appendix A), run by a scratch re-implementation of it: no number
  of any kind outside the slots, in digits or in words, no "tomorrow", no %, no ₪, no product name.
  The samples were given to the page only while these pictures were taken. They are not in the
  app's data, and not in the example file;
- **every figure on the cards is the engine's own** over the test shop: each slot is filled from
  that suggestion's published facts, as FR-238's table says;
- **מים is drawn without the stand-in boost.** Today's example shows "Expected sales raised 10%,
  the model's estimate", but that pick is a fixed test answer that no model gave. F14-S1 now proposes
  (OQ-1403, waiting on you) that the example show no stand-in pick, so מים's box says the model was
  not asked about it tonight, and its order is 21 instead of the boosted 23.

## What you are asked to decide

1. **The card** (FR-242). When a suggestion has an explanation, it replaces the engine's sentence
   ("You'll sell about … before your next order …") and the shelf-life line ("Only what sells in
   2 days …"), after the same **AI** tag Shelf plan uses. The quantity, the "Your stock count wasn't
   used" notice, the market box and the three buttons stay exactly as they are. A card without an
   explanation is today's card, with no tag.
2. **The note above the suggestions** (FR-243), once, in Shelf plan's AI box. It has four states:
   - every suggestion explained: what the AI does;
   - some explained: what the AI does, and how many of tonight's it explained;
   - none explained: that the AI has not explained tonight's suggestions;
   - no model key: that the AI's explanations are off.

   There is no note when there are no suggestions, or while Reorder waits for daily sales.
3. **The phrases that carry the figures** (FR-238, C-79), in the three languages (table below).
   The AI writes no number. It writes a slot such as `{left}`, and the page puts in a phrase like
   "about 3 left on the order day". Only `{next_order}` carries the date ("your order on Sunday
   30 Aug, for the 7 days until the next one"), and every explanation names it once. The Hebrew and Arabic
   phrases are new, proposed here.
4. **What the pictures showed, and what changed because of it** (see "What the pictures show").

## The screens

### The example today, before the AI is asked

What the example will show until its explanations are written once with the key (FR-244): every
card shows the engine's sentence, and the note says the AI has not explained tonight's suggestions.

| العربية | עברית |
|---|---|
| ![None explained yet, Arabic](F14-screens-mockups/none-ar.png) | ![None explained yet, Hebrew](F14-screens-mockups/none-he.png) |

### Every suggestion explained

All six cards with an explanation (hand-written samples).

| العربية | עברית |
|---|---|
| ![All explained, Arabic](F14-screens-mockups/all-ar.png) | ![All explained, Hebrew](F14-screens-mockups/all-he.png) |

In English: ![All explained, English](F14-screens-mockups/all-en.png)

### Some explained

Four of six. ביסלי גריל's explanation was held back by the check, and מים's was not written
tonight. Both show the engine's sentence, as the note says.

| العربية | עברית |
|---|---|
| ![Some explained, Arabic](F14-screens-mockups/some-ar.png) | ![Some explained, Hebrew](F14-screens-mockups/some-he.png) |

### No model key

| العربية | עברית |
|---|---|
| ![No model key, Arabic](F14-screens-mockups/nokey-ar.png) | ![No model key, Hebrew](F14-screens-mockups/nokey-he.png) |

### Each kind of card, close up

| Card | What it shows | العربية | עברית | English |
|---|---|---|---|---|
| במבה | stock gone by the order day: `{runs_out}`; the weeks: `{weeks}` | ![](F14-screens-mockups/card-bamba-ar.png) | ![](F14-screens-mockups/card-bamba-he.png) | ![](F14-screens-mockups/card-bamba-en.png) |
| ביסלי גריל | the stock count not used (gross): the notice stays under the AI's text | ![](F14-screens-mockups/card-bissli-ar.png) | ![](F14-screens-mockups/card-bissli-he.png) | ![](F14-screens-mockups/card-bissli-en.png) |
| לחם אחיד | capped by a 2-day shelf life: `{capped}` | ![](F14-screens-mockups/card-bread-ar.png) | ![](F14-screens-mockups/card-bread-he.png) | ![](F14-screens-mockups/card-bread-en.png) |
| פיתות | capped, a second wording | ![](F14-screens-mockups/card-pitas-ar.png) | ![](F14-screens-mockups/card-pitas-he.png) | ![](F14-screens-mockups/card-pitas-en.png) |
| מים | the order day and its days: `{next_order}`; the market box without the stand-in boost | ![](F14-screens-mockups/card-water-ar.png) | ![](F14-screens-mockups/card-water-he.png) | ![](F14-screens-mockups/card-water-en.png) |
| קולה | stock left on the order day: `{left}` | ![](F14-screens-mockups/card-cola-ar.png) | ![](F14-screens-mockups/card-cola-he.png) | ![](F14-screens-mockups/card-cola-en.png) |

## What the pictures show

1. **The date repeated (changed).** In the first drawing each phrase named its own date, so a text
   using `{next_order}`, `{expected}` and `{runs_out}` said "Sunday 30 Aug" three times. Now only
   `{next_order}` carries the date, every text names it once, and the other phrases say "the order
   day", in Hebrew and Arabic in the construct form (יום ההזמנה, يوم الطلب), never היום or اليوم,
   which the check refuses as "today". F14-S1 takes this change.
2. **Hebrew and Arabic cannot agree with the product.** The model is never sent the product's name
   (FR-236), and one text may serve another product of the same department (FR-239), so it cannot
   know whether the name is masculine, feminine or plural. The samples are written around that,
   with "the sales of {product}" (המכירות של / مبيعات) or "{product} has" (ל… יש / لدى) rather than
   "{product} sells". F14-S1's prompt asks the model for the same.
3. **Arabic "لـ" before a Hebrew name (changed).** The first samples wrote لـ{product}, which
   leaves the Arabic letter hanging before a Hebrew name ("لـלחם אחיד"). The samples now use
   لدى or مبيعات before the name, and never join a letter to it.
4. **"Your order on …" says "for the 7 days until the next one" (changed).** It said "which covers
   7 days", which read as untrue beside a capped order (bread covers 2 days, not 7). The English
   samples open with "Ahead of" or "In" before it, never "For", so it never reads "for … for".
5. **The weeks' figures in Hebrew and Arabic.** `{weeks}` lists each week's units, oldest first. In
   this test shop every week sold the same, so the pictures cannot show a list of different figures.
   Each card's words were measured on screen and read in the right order from right to left; a list
   of different figures is checked when the page is built.

## The words

### The tag and the note

| Key | English | עברית | العربية |
|---|---|---|---|
| tag (Shelf plan's) | AI | AI | AI |
| note: what the AI does | An AI writes each card's explanation from that suggestion's facts. It explains the quantity and does not change it. | בינה מלאכותית כותבת את ההסבר של כל כרטיס מתוך הנתונים של אותה הצעה. היא מסבירה את הכמות ואינה משנה אותה. | يكتب ذكاء اصطناعي شرح كل بطاقة من معطيات ذلك الاقتراح. يشرح الكمية ولا يغيّرها. |
| note: some explained | Tonight the AI explained {n} of {total} suggestions. A card it did not explain shows the engine's sentence. | הלילה הבינה המלאכותית הסבירה {n} מתוך {total} הצעות. כרטיס שלא הוסבר מציג את המשפט של המנוע. | الليلة شرح الذكاء الاصطناعي {n} من {total} اقتراحات. البطاقة التي لم يشرحها تعرض جملة المحرّك. |
| note: none explained | The AI has not explained tonight's suggestions. | הבינה המלאכותית לא הסבירה את ההצעות של הלילה. | لم يشرح الذكاء الاصطناعي اقتراحات الليلة. |
| note: no model key | The AI's explanations are off: no key for the model has been set up. | ההסברים של הבינה המלאכותית כבויים: לא הוגדר מפתח למודל. | شروح الذكاء الاصطناعي متوقّفة: لم يُضبط مفتاح للنموذج. |

### The phrases that carry the figures (FR-238)

The figures and dates in braces are the card's own: one decimal, the card's words for a number of
days, and its date format. `{runs_out}` and `{capped}` are the card's own sentences today.

| Slot | English | עברית | العربية |
|---|---|---|---|
| `{quantity}` | an order of {n} | הזמנה של {n} | طلبية من {n} |
| `{expected}` | about {expected} expected to sell in the {days} from the order day | צפי מכירות של בערך {expected} במשך {days} החל מיום ההזמנה | مبيعات متوقَّعة بنحو {expected} خلال {days} ابتداءً من يوم الطلب |
| `{weeks}` | {list} sold in the {weeks} to {date} | {list} נמכרו במשך {weeks} עד {date} | {list} بيعت خلال {weeks} حتى {date} |
| `{next_order}` | your order on {day}, for the {days} until the next one | ההזמנה שלך ב{day}, למשך {days} עד ההזמנה הבאה | طلبك يوم {day}، لمدة {days} حتى الطلب التالي |
| `{left}` | about {left} left on the order day | בערך {left} שעוד יהיו על המדף ביום ההזמנה | نحو {left} ستبقى على الرف يوم الطلب |
| `{runs_out}` | what you have will be gone by the order day | מה שיש לך ייגמר עד יום ההזמנה | سينفد ما لديك قبل يوم الطلب |
| `{capped}` | only what sells in {days}, before it spoils | רק מה שנמכר תוך {days}, לפני שהוא מתקלקל | فقط ما يُباع خلال {days}، قبل أن يتلف |
| `{product}` | the product's name | שם המוצר | اسم المنتج |

### The hand-written samples (NOT the model's)

Written only to draw the cards. The model's own texts will differ. Each passes FR-238's check.

| Card | English | עברית | العربية |
|---|---|---|---|
| במבה | Sales of {product} have held steady: {weeks}. Ahead of {next_order}, that means {expected}. Since {runs_out}, the suggestion orders all of it. | המכירות של {product} יציבות: {weeks}. עבור {next_order}, המשמעות היא {expected}. מכיוון ש{runs_out}, ההצעה מזמינה את כל הכמות הזאת. | مبيعات {product} ثابتة: {weeks}. وبالنسبة إلى {next_order}، يعني ذلك {expected}. وبما أنه {runs_out}، يطلب الاقتراح الكمية كلها. |
| ביסלי גריל | Sales of {product} are the same every week: {weeks}. Your stock count could not be used, so in {next_order}, the suggestion rests on sales alone: {expected}. | המכירות של {product} זהות בכל שבוע: {weeks}. לא ניתן היה להשתמש בספירת המלאי, ולכן עבור {next_order}, ההצעה נשענת על המכירות בלבד: {expected}. | مبيعات {product} متساوية كل أسبوع: {weeks}. لم يكن ممكنًا استخدام جرد مخزونك، لذلك بالنسبة إلى {next_order}، يعتمد الاقتراح على المبيعات وحدها: {expected}. |
| לחם אחיד | {product} has {expected}, but the shelf life is short. So in {next_order}, the suggestion is {capped}. And {runs_out}. | ל{product} יש {expected}, אבל חיי המדף קצרים. לכן עבור {next_order}, ההצעה היא {capped}. ו{runs_out}. | لدى {product} {expected}، لكن مدة الصلاحية قصيرة. لذلك بالنسبة إلى {next_order}، الاقتراح هو {capped}. و{runs_out}. |
| פיתות | Sales of {product} outpace the shelf life: there are {expected}. In {next_order}, the suggestion is {capped}, and {runs_out}. | המכירות של {product} מהירות יותר מחיי המדף: יש {expected}. עבור {next_order}, ההצעה היא {capped}, ו{runs_out}. | مبيعات {product} أسرع من مدة الصلاحية: هناك {expected}. وبالنسبة إلى {next_order}، الاقتراح هو {capped}، و{runs_out}. |
| מים | Ahead of {next_order}, {product} has {expected}. Since {runs_out}, the suggestion replaces all of it. | עבור {next_order}, ל{product} יש {expected}. מכיוון ש{runs_out}, ההצעה מחליפה את כל הכמות הזאת. | بالنسبة إلى {next_order}، لدى {product} {expected}. وبما أنه {runs_out}، يعوّض الاقتراح الكمية كلها. |
| קולה | Ahead of {next_order}, {product} has {expected}, and {left}. So the suggestion orders only what the shelf will lack. | עבור {next_order}, ל{product} יש {expected}, ו{left}. לכן ההצעה מזמינה רק את מה שיחסר על המדף. | بالنسبة إلى {next_order}، لدى {product} {expected}، و{left}. لذلك يطلب الاقتراح فقط ما سينقص على الرف. |
