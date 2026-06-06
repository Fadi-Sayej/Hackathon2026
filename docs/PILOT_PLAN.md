# SmartShelf AI — Pilot Plan

---

## Pilot Scope

- **Duration:** 30 days
- **Number of stores:** 3 (ideally: 1 gas station convenience store, 1 mini-market, 1 makolet)
- **Store size:** 500–2,500 active SKUs
- **Geographic focus:** Tel Aviv metropolitan area (allows for competitor price validation using the same neighborhood snapshot)
- **Team commitment:** Weekly 30-minute check-in call per store. Data collection on day 1, day 15, and day 30.

---

## What the Store Owner Does

| Action | Frequency | Time required |
|---|---|---|
| Export POS inventory CSV | Weekly (Monday morning) | 5 minutes |
| Upload CSV to SmartShelf AI | Weekly | 2 minutes |
| Review and approve recommendations | Daily (or as prompted) | 5–10 minutes |
| Log expiry dates at receiving | As product arrives | 1 minute per delivery |
| Record stockout incidents (manual backup) | As they occur | 30 seconds per event |

**Total time commitment from store owner:** Under 15 minutes per day.

---

## What Gets Measured

### Before pilot starts (baseline)

1. How long does the store owner currently spend on ordering decisions per day? (Self-reported, timed)
2. How many stockout incidents in the past 30 days? (POS data or owner estimate)
3. How many products expired in the past 30 days? (Owner estimate or waste log)
4. Current stock accuracy: spot-check 20 random SKUs, count mismatches between POS and physical count.

### During pilot (weekly)

- Number of recommendations reviewed per week
- Number approved, rejected, edited
- Time to complete ordering workflow (timed by owner or by app log)
- Any stockout incidents (owner-reported)

### After 30 days (outcome)

1. Time-to-order: minutes per ordering session vs. baseline
2. Stockout incidents: count in pilot month vs. baseline month
3. Waste events: products logged as expired in pilot month vs. baseline
4. Stock accuracy: repeat the 20-SKU spot-check
5. Net promoter score: "Would you recommend this tool to another store owner?" (0–10)

---

## Success Definition

The pilot succeeds if, after 30 days, at least two of the following are true:

| Metric | Target |
|---|---|
| Ordering time | Reduced by at least 50% vs. baseline |
| Stockout incidents | At least 20% fewer than the baseline month |
| Expired products | At least one near-expiry product caught and cleared before loss |
| Owner NPS | Score ≥ 7 from at least 2 of 3 store owners |

If all four are met, the pilot is a strong product-market fit signal and justifies moving to Phase 3 (paid subscription).

---

## What SmartShelf AI Provides During Pilot

- Free access to the full app (Phase 1 feature set)
- Onboarding session: 30 minutes to walk the owner through the workflow
- CSV import template compatible with the store's POS format
- WhatsApp support line during business hours for the duration of the pilot
- Summary report at day 30 showing before/after metrics

---

## Pilot Limitations (honest)

- App is local-first: each device has its own localStorage. Multiple devices in the same store do not sync until Phase 3.
- Sales history in the analytics uses the last known POS snapshot — accuracy improves with weekly imports but is not real-time.
- Competitor prices remain the mock neighborhood snapshot unless the store is in the Tel Aviv reference area and the live pipeline is activated.
- If the store's POS export uses non-standard column names, the team will manually configure the column mapping before the pilot starts.
