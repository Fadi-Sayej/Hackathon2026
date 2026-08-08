// Pilot telemetry aggregation (nagham.md B-3).
//
// "Did this help?" is the pilot's entire purpose, and this module is the answer
// engine. It joins two things:
//
//   • the SHOWN set — the operational recommendations the manager was presented
//     with, scored for money-at-stake by the SAME actionPriority engine the
//     store-floor screen uses, so the ₪ figures here can never disagree with
//     what the manager saw (PLAN.md §4: no number we cannot explain), and
//   • the DECIDED set — every decision recorded through persistence (Done /
//     Dismissed + reason / Snoozed), which B-2 mirrors to Firestore so the four
//     of us see the manager's real actions, not one browser's.
//
// It is pure (no React, no DOM, no storage) so the numbers are unit-tested
// directly. The view layer only renders what this returns.

import { rankActions } from '../lib/analytics/actionPriority.js'
import {
  ACTION_STATUS,
  DISMISS_REASON,
  DISMISS_REASON_ORDER,
  normalizeStatus,
} from '../lib/operational/completionActions.js'

const TYPE_LABEL = {
  CHECK_MARGIN: 'Selling below cost',
  CHECK_WOLT_PRICE_GAP: 'WOLT price gap',
  PROMOTE_EXPIRING_PRODUCT: 'Expiring',
  CHECK_NEGATIVE_STOCK: 'Stock count wrong',
  VERIFY_UNKNOWN_BARCODE: 'No barcode',
}

export function typeLabel(type) {
  return TYPE_LABEL[type] ?? type ?? 'Unknown'
}

// A decision counts as "accepted / acted on" when the manager marked it Done.
// Legacy reorder records used APPROVED; treat it the same so old data still reads.
function isAccepted(status) {
  return status === ACTION_STATUS.DONE || status === 'APPROVED'
}

function isDismissed(status) {
  return status === ACTION_STATUS.DISMISSED || status === 'REJECTED'
}

function num(value) {
  return Number.isFinite(value) ? value : 0
}

function safeRate(numerator, denominator) {
  return denominator > 0 ? numerator / denominator : 0
}

/**
 * Build the full telemetry summary.
 *
 * @param {Array} recommendations  the shown set (operationalData.recommendations)
 * @param {Object} decisions       id → decision record (loadRecommendationDecisions())
 */
export function buildTelemetry(recommendations = [], decisions = {}) {
  const decisionMap = decisions && typeof decisions === 'object' ? decisions : {}
  const { money, data } = rankActions(recommendations)
  const shown = [...money, ...data] // each carries impactIls + group from the same engine

  const byType = new Map()
  const ensureType = (type) => {
    if (!byType.has(type)) {
      byType.set(type, {
        type,
        label: typeLabel(type),
        shown: 0,
        done: 0,
        dismissed: 0,
        snoozed: 0,
        ignored: 0,
        potentialImpactIls: 0,
        capturedImpactIls: 0,
        isMoney: false,
      })
    }
    return byType.get(type)
  }

  let totalShown = 0
  let totalMoneyShown = 0
  let potentialImpactIls = 0

  for (const rec of shown) {
    const row = ensureType(rec.type)
    row.shown += 1
    totalShown += 1
    if (rec.group === 'money') {
      row.isMoney = true
      totalMoneyShown += 1
      row.potentialImpactIls += num(rec.impactIls)
      potentialImpactIls += num(rec.impactIls)
    }

    const decision = decisionMap[rec.id]
    const status = decision ? normalizeStatus(decision.status) : null

    if (!decision) {
      row.ignored += 1
    } else if (isAccepted(status)) {
      row.done += 1
      // Prefer the ₪ recorded on the decision at the moment it was made; fall
      // back to re-scoring the shown rec so a pre-#31 record still counts.
      const captured = Number.isFinite(decision.impactIls)
        ? decision.impactIls
        : num(rec.impactIls)
      row.capturedImpactIls += captured
    } else if (isDismissed(status)) {
      row.dismissed += 1
    } else if (status === ACTION_STATUS.SNOOZED) {
      row.snoozed += 1
    } else {
      row.ignored += 1
    }
  }

  const typeRows = [...byType.values()]
    .map((row) => ({
      ...row,
      // Two rates, because they answer different questions:
      //  • acceptanceRate (done ÷ shown) — coverage of the whole backlog.
      //  • engagedRate (done ÷ decided) — of the ones the manager actually
      //    touched, how many did they accept. This is the trust signal and is
      //    not distorted by the long tail nobody reaches in a ten-minute morning.
      acceptanceRate: safeRate(row.done, row.shown),
      engagedRate: safeRate(row.done, row.done + row.dismissed),
      actedOn: row.done + row.dismissed,
    }))
    // Money types first, then by how many were acted on.
    .sort((a, b) => Number(b.isMoney) - Number(a.isMoney) || b.actedOn - a.actedOn)

  // Dismissal-reason breakdown — PLAN.md §5's most important row. A high
  // WRONG_DATA share on a type is the signal to cut that alert, not tune it.
  const reasonCounts = Object.fromEntries(DISMISS_REASON_ORDER.map((r) => [r, 0]))
  let reasonUnknown = 0
  let totalDismissed = 0
  let totalDone = 0
  let totalSnoozed = 0
  let capturedImpactIls = 0

  for (const [id, decision] of Object.entries(decisionMap)) {
    const status = normalizeStatus(decision.status)
    if (isAccepted(status)) {
      totalDone += 1
    } else if (isDismissed(status)) {
      totalDismissed += 1
      const reason = decision.reason
      if (reason && Object.prototype.hasOwnProperty.call(reasonCounts, reason)) {
        reasonCounts[reason] += 1
      } else {
        reasonUnknown += 1
      }
    } else if (status === ACTION_STATUS.SNOOZED) {
      totalSnoozed += 1
    }
    void id
  }

  for (const row of typeRows) capturedImpactIls += row.capturedImpactIls

  const actedOn = totalDone + totalDismissed
  const decidedTotal = actedOn + totalSnoozed

  const recentDecisions = Object.entries(decisionMap)
    .map(([id, d]) => ({
      id,
      status: normalizeStatus(d.status),
      reason: d.reason ?? null,
      type: d.type ?? null,
      productName: d.productName ?? null,
      impactIls: Number.isFinite(d.impactIls) ? d.impactIls : null,
      at: d.decidedAt || d.updatedAt || d.at || null,
    }))
    .sort((a, b) => String(b.at ?? '').localeCompare(String(a.at ?? '')))
    .slice(0, 25)

  return {
    totalShown,
    totalMoneyShown,
    totalDataShown: totalShown - totalMoneyShown,
    decidedTotal,
    actedOn,
    totalDone,
    totalDismissed,
    totalSnoozed,
    ignored: Math.max(totalShown - decidedTotal, 0),
    acceptanceRate: safeRate(totalDone, totalShown),
    engagedAcceptanceRate: safeRate(totalDone, totalDone + totalDismissed),
    coverageRate: safeRate(decidedTotal, totalShown),
    potentialImpactIls,
    capturedImpactIls,
    wrongDataDismissals: reasonCounts[DISMISS_REASON.WRONG_DATA] ?? 0,
    wrongDataRate: safeRate(reasonCounts[DISMISS_REASON.WRONG_DATA] ?? 0, totalDismissed),
    reasonCounts,
    reasonUnknown,
    typeRows,
    recentDecisions,
  }
}
