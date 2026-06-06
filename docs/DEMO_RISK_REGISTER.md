# SmartShelf AI — Demo Risk Register

Last updated: 2026-06-06

---

## Known Demo-Breaking Bugs

No demo-breaking bugs are currently known from code inspection. The codebase is clean (lint passes, build passes). This section will be updated if issues are discovered during live QA.

---

## Non-Blocking Issues

| ID | Issue | Severity | Impact on Demo | Mitigation |
|---|---|---|---|---|
| NB-01 | "Send to Supplier" shows a toast but sends nothing | LOW | Visible if judges ask "does this actually send?" | Say: "This triggers the confirmation flow; the actual supplier API transmission is a post-hackathon integration step." |
| NB-02 | Shelf Compliance vision analysis is mocked (generateMockDetectedShelf) | LOW | Visible if judges ask for the real photo result | Say: "This shows the workflow — upload, analyze, compare against planogram. The vision model integration is the next step." |
| NB-03 | Competitor prices are a mock neighborhood (6 barcodes, 4 stores) | MEDIUM | Visible if judges check whether prices are real | Say: "These come from the Israeli food price transparency law format — we've modeled a realistic neighborhood. The pipeline to pull live data is built." |
| NB-04 | AI explanations are rule-based by default (not Gemini) | MEDIUM | Visible if judges ask "is this real AI?" | Say: "The default uses deterministic retail analytics so the demo stays stable. The Gemini proxy is built and can run locally." |
| NB-05 | Market context uses static fallback by default | LOW | Panel source label says "fallback" | Say: "We run with a stable snapshot during demo. One env variable switches to live Open-Meteo and holiday APIs." |
| NB-06 | Comax connector returns an error immediately | LOW | Only visible if someone clicks Comax on Data Source page | Avoid navigating to Data Source page during the demo. |
| NB-07 | Sales history figures in demo dataset are synthetic | LOW | Underlying data, not prominently displayed | If asked: "Sales velocity is estimated in the demo. A real POS import provides actuals." |

---

## Actions to Avoid During Demo

| Action | Why to Avoid | Fallback If Accidentally Clicked |
|---|---|---|
| Click "Comax" on Data Source page | Shows an error message immediately | Say: "Comax integration is the next step — this is the connector slot." |
| Upload a CSV with unexpected columns | May show validation warnings or fail silently | Switch back to Demo Data connector via Data Source page |
| Approve a recommendation with quantity 0 | Approve button is disabled — may confuse judges if not explained | Explain: "The system requires a valid quantity before approving — a guard against zero-dollar orders." |
| Open browser console in front of judges | May show non-critical React warnings | Close DevTools before presenting |
| Reload the page mid-demo without knowing localStorage state | May show recommendations in unexpected state | Click Reset Demo State first to start clean |
| Try to print with a popup blocker active | Browser may silently block window.print() | Test print before the demo and whitelist localhost in browser settings |

---

## Risk Severity Definitions

- **HIGH** — Demo stops or crashes. Present shows an error, blank screen, or broken flow.
- **MEDIUM** — Demo continues but a claim must be walked back or explained under pressure.
- **LOW** — Minor friction; a one-line explanation is sufficient and credible.

---

## Current Overall Risk Level

**LOW-MEDIUM.** The app is structurally sound. All mock elements are labeled or easily explained. The main risk is a judge pressing hard on AI authenticity or supplier transmission. Both have honest, confident answers (see `JUDGE_QA.md`).
