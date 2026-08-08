import { useEffect, useMemo, useState } from 'react'

import { loadOperationalData } from '../lib/dataAdapters/loadOperationalData.js'
import {
  loadRecommendationDecisions,
  subscribeToPersistence,
} from '../lib/persistence/persistence.js'
import { isFirebaseConfigured, STORE_ID } from '../firebase.js'
import {
  ACTION_STATUS,
  DISMISS_REASON,
  DISMISS_REASON_ORDER,
  OUTCOME_LABEL,
  dismissReasonLabel,
} from '../lib/operational/completionActions.js'
import { formatShekel, formatDate } from '../lib/utils/format.js'
import { buildTelemetry } from './telemetryModel.js'

const pct = (rate) => `${Math.round((rate ?? 0) * 100)}%`

// The credibility target for wrong-data dismissals (PLAN.md §5, last row).
const WRONG_DATA_TARGET = 0.1

function Metric({ label, value, detail, tone = 'neutral' }) {
  return (
    <div className={`t-card t-card-${tone}`}>
      <div className="t-card-label">{label}</div>
      <div className="t-card-value">{value}</div>
      {detail ? <div className="t-card-detail">{detail}</div> : null}
    </div>
  )
}

function Bar({ rate }) {
  return (
    <div className="t-bar">
      <div className="t-bar-fill" style={{ width: `${Math.round((rate ?? 0) * 100)}%` }} />
    </div>
  )
}

export function TelemetryDashboard() {
  const [operationalData, setOperationalData] = useState({ recommendations: [], meta: {} })
  const [decisions, setDecisions] = useState(() => loadRecommendationDecisions())
  const [status, setStatus] = useState('loading')

  useEffect(() => {
    let cancelled = false
    loadOperationalData().then((data) => {
      if (cancelled) return
      setOperationalData(data)
      setStatus('ready')
    })
    return () => {
      cancelled = true
    }
  }, [])

  // Refresh decisions whenever a background cloud sync updates the local mirror
  // (another device, or offline writes reconciling on reconnect).
  useEffect(() => {
    const refresh = () => setDecisions(loadRecommendationDecisions())
    const unsubscribe = subscribeToPersistence(refresh)
    if (typeof window !== 'undefined') {
      window.addEventListener('smartshelf:persistence-updated', refresh)
      window.addEventListener('focus', refresh)
    }
    return () => {
      unsubscribe()
      if (typeof window !== 'undefined') {
        window.removeEventListener('smartshelf:persistence-updated', refresh)
        window.removeEventListener('focus', refresh)
      }
    }
  }, [])

  const t = useMemo(
    () => buildTelemetry(operationalData.recommendations ?? [], decisions),
    [operationalData, decisions],
  )

  const cloudLive = isFirebaseConfigured()
  const generatedAt = operationalData.meta?.generatedAt

  return (
    <div className="t-root">
      <style>{STYLES}</style>

      <header className="t-header">
        <div>
          <p className="t-eyebrow">SmartShelf · Pilot telemetry</p>
          <h1>Did the alerts help?</h1>
          <p className="t-sub">
            Internal view for the team. Every alert shown and every decision the manager made,
            so we can answer acceptance and ₪ impact without opening a terminal.
          </p>
        </div>
        <div className="t-source">
          <span className={`t-dot ${cloudLive ? 't-dot-live' : 't-dot-local'}`} />
          {cloudLive ? `Firestore · ${STORE_ID}` : 'localStorage (this device only)'}
          <button className="t-reload" onClick={() => setDecisions(loadRecommendationDecisions())}>
            Reload
          </button>
        </div>
      </header>

      {status === 'loading' ? (
        <p className="t-note">Loading the latest export…</p>
      ) : (
        <>
          <section className="t-grid">
            <Metric
              label="Alerts shown"
              value={t.totalShown.toLocaleString()}
              detail={`${t.totalMoneyShown.toLocaleString()} money · ${t.totalDataShown.toLocaleString()} data`}
              tone="info"
            />
            <Metric
              label="Acted on"
              value={t.actedOn.toLocaleString()}
              detail={`${t.totalDone} done · ${t.totalDismissed} dismissed · ${t.totalSnoozed} snoozed`}
              tone={t.actedOn ? 'good' : 'neutral'}
            />
            <Metric
              label="Acceptance rate"
              value={pct(t.engagedAcceptanceRate)}
              detail={`Done ÷ decided · ${pct(t.coverageRate)} of backlog touched · target > 30%`}
              tone={t.engagedAcceptanceRate >= 0.3 ? 'good' : 'neutral'}
            />
            <Metric
              label="₪ impact captured"
              value={formatShekel(t.capturedImpactIls)}
              detail="Per sale, on actions marked done"
              tone={t.capturedImpactIls > 0 ? 'good' : 'neutral'}
            />
          </section>

          {t.actedOn === 0 && t.totalSnoozed === 0 ? (
            <p className="t-note">
              No decisions recorded yet. Once the manager works the daily action list, acceptance
              and ₪ impact populate here. Potential ₪ at stake across today&apos;s money alerts:{' '}
              <strong>{formatShekel(t.potentialImpactIls)}</strong> per sale.
            </p>
          ) : null}

          <section className="t-panel">
            <h2>Which alert types earn their place</h2>
            <p className="t-panel-sub">
              Acceptance rate by type is how we decide what to keep. A type nobody acts on is a
              type to drop.
            </p>
            <table className="t-table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th className="t-num">Shown</th>
                  <th className="t-num">Done</th>
                  <th className="t-num">Dismissed</th>
                  <th className="t-num">Snoozed</th>
                  <th className="t-num">Ignored</th>
                  <th className="t-accept">Accept. of decided</th>
                  <th className="t-num">₪ captured</th>
                </tr>
              </thead>
              <tbody>
                {t.typeRows.map((row) => (
                  <tr key={row.type}>
                    <td>
                      <span className="t-type">{row.label}</span>
                      {row.isMoney ? <span className="t-tag t-tag-money">money</span> : (
                        <span className="t-tag t-tag-data">data</span>
                      )}
                    </td>
                    <td className="t-num">{row.shown.toLocaleString()}</td>
                    <td className="t-num">{row.done}</td>
                    <td className="t-num">{row.dismissed}</td>
                    <td className="t-num">{row.snoozed}</td>
                    <td className="t-num t-muted">{row.ignored.toLocaleString()}</td>
                    <td className="t-accept">
                      <div className="t-accept-cell">
                        <Bar rate={row.engagedRate} />
                        <span>{row.actedOn ? pct(row.engagedRate) : '—'}</span>
                      </div>
                    </td>
                    <td className="t-num">
                      {row.isMoney ? formatShekel(row.capturedImpactIls) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section className="t-panel">
            <h2>Why alerts were dismissed</h2>
            <p className="t-panel-sub">
              The single most important signal in the pilot. A tool that is confidently wrong is
              worse than no tool, so “the data is wrong” dismissals are tracked against a{' '}
              &lt; {pct(WRONG_DATA_TARGET)} target.
            </p>
            <div className="t-reasons">
              <div className={`t-reason ${t.wrongDataRate > WRONG_DATA_TARGET ? 't-reason-alarm' : 't-reason-ok'}`}>
                <div className="t-reason-count">{t.wrongDataDismissals}</div>
                <div className="t-reason-label">{dismissReasonLabel(DISMISS_REASON.WRONG_DATA)}</div>
                <div className="t-reason-rate">
                  {t.totalDismissed ? `${pct(t.wrongDataRate)} of dismissals` : 'no dismissals yet'}
                </div>
              </div>
              {DISMISS_REASON_ORDER.filter((r) => r !== DISMISS_REASON.WRONG_DATA).map((reason) => (
                <div className="t-reason" key={reason}>
                  <div className="t-reason-count">{t.reasonCounts[reason] ?? 0}</div>
                  <div className="t-reason-label">{dismissReasonLabel(reason)}</div>
                </div>
              ))}
              <div className="t-reason">
                <div className="t-reason-count">{t.reasonUnknown}</div>
                <div className="t-reason-label">Reason not recorded</div>
              </div>
            </div>
          </section>

          <section className="t-panel">
            <h2>Recent decisions</h2>
            {t.recentDecisions.length === 0 ? (
              <p className="t-panel-sub">Nothing yet.</p>
            ) : (
              <table className="t-table">
                <thead>
                  <tr>
                    <th>When</th>
                    <th>Product</th>
                    <th>Type</th>
                    <th>Outcome</th>
                    <th className="t-num">₪</th>
                  </tr>
                </thead>
                <tbody>
                  {t.recentDecisions.map((d) => (
                    <tr key={d.id}>
                      <td className="t-muted">{d.at ? formatDate(d.at) : '—'}</td>
                      <td dir="auto">{d.productName ?? d.id}</td>
                      <td className="t-muted">{d.type ?? '—'}</td>
                      <td>
                        <span className={`t-outcome t-outcome-${(d.status ?? '').toLowerCase()}`}>
                          {OUTCOME_LABEL[d.status] ?? d.status ?? '—'}
                        </span>
                        {d.status === ACTION_STATUS.DISMISSED ? (
                          <span className="t-muted"> · {dismissReasonLabel(d.reason)}</span>
                        ) : null}
                      </td>
                      <td className="t-num">{d.impactIls != null ? formatShekel(d.impactIls) : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          <footer className="t-foot">
            <p>
              Acceptance rate is done ÷ decided (of the alerts the manager actually engaged with) —
              we don&apos;t log per-alert impressions, so a true done ÷ shown would understate trust
              against the whole {t.totalShown.toLocaleString()}-item backlog; coverage is shown
              alongside it. ₪ figures are per sale, deliberately not multiplied by volume —
              YomYom&apos;s stock counts are unreliable, so a lot value would be a guess dressed up
              as a number. “Shown” is the current pipeline export
              {generatedAt ? `, generated ${formatDate(generatedAt)}` : ''}. Capture a week-0
              baseline before go-live, or no improvement can be attributed to us.
            </p>
          </footer>
        </>
      )}
    </div>
  )
}

const STYLES = `
.t-root { max-width: 1040px; margin: 0 auto; padding: 2rem 1.25rem 4rem; color: #e7ecf3;
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
.t-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem;
  flex-wrap: wrap; border-bottom: 1px solid #263041; padding-bottom: 1.25rem; margin-bottom: 1.5rem; }
.t-eyebrow { text-transform: uppercase; letter-spacing: .08em; font-size: .72rem; color: #7f8ea8; margin: 0 0 .35rem; }
.t-header h1 { margin: 0 0 .4rem; font-size: 1.7rem; }
.t-sub { margin: 0; color: #9fb0c6; max-width: 62ch; font-size: .92rem; line-height: 1.5; }
.t-source { display: flex; align-items: center; gap: .5rem; font-size: .82rem; color: #9fb0c6; white-space: nowrap; }
.t-dot { width: .6rem; height: .6rem; border-radius: 50%; display: inline-block; }
.t-dot-live { background: #34d399; box-shadow: 0 0 0 3px rgba(52,211,153,.18); }
.t-dot-local { background: #fbbf24; box-shadow: 0 0 0 3px rgba(251,191,36,.18); }
.t-reload { margin-left: .5rem; background: #1c2635; color: #cdd7e6; border: 1px solid #33415a;
  border-radius: 7px; padding: .3rem .6rem; cursor: pointer; font-size: .8rem; }
.t-reload:hover { background: #24324a; }
.t-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: .9rem; margin-bottom: 1.75rem; }
.t-card { background: #141b27; border: 1px solid #232f42; border-radius: 12px; padding: 1rem 1.1rem; }
.t-card-good { border-color: #2f6b52; }
.t-card-info { border-color: #2b4a6b; }
.t-card-label { font-size: .78rem; color: #8ba0bb; margin-bottom: .4rem; }
.t-card-value { font-size: 1.7rem; font-weight: 650; }
.t-card-detail { font-size: .76rem; color: #7f8ea8; margin-top: .3rem; }
.t-panel { background: #10151f; border: 1px solid #1f2937; border-radius: 14px; padding: 1.25rem 1.35rem; margin-bottom: 1.35rem; }
.t-panel h2 { margin: 0 0 .3rem; font-size: 1.12rem; }
.t-panel-sub { margin: 0 0 1rem; color: #93a4bd; font-size: .86rem; max-width: 74ch; line-height: 1.5; }
.t-table { width: 100%; border-collapse: collapse; font-size: .88rem; }
.t-table th { text-align: left; color: #7f8ea8; font-weight: 550; font-size: .76rem; text-transform: uppercase;
  letter-spacing: .04em; padding: .4rem .55rem; border-bottom: 1px solid #232f42; }
.t-table td { padding: .55rem; border-bottom: 1px solid #171f2b; vertical-align: middle; }
.t-num { text-align: right; font-variant-numeric: tabular-nums; }
.t-muted { color: #6f7f97; }
.t-type { font-weight: 550; }
.t-tag { font-size: .64rem; text-transform: uppercase; letter-spacing: .05em; padding: .1rem .4rem;
  border-radius: 5px; margin-left: .5rem; }
.t-tag-money { background: rgba(52,211,153,.14); color: #6ee7b7; }
.t-tag-data { background: rgba(148,163,184,.14); color: #b6c2d4; }
.t-accept-cell { display: flex; align-items: center; gap: .55rem; min-width: 130px; }
.t-bar { flex: 1; height: 7px; background: #1c2636; border-radius: 4px; overflow: hidden; }
.t-bar-fill { height: 100%; background: linear-gradient(90deg, #38bdf8, #34d399); }
.t-reasons { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: .8rem; }
.t-reason { background: #141b27; border: 1px solid #232f42; border-radius: 11px; padding: .9rem 1rem; }
.t-reason-alarm { border-color: #7f1d1d; background: rgba(127,29,29,.18); }
.t-reason-ok { border-color: #2f6b52; }
.t-reason-count { font-size: 1.5rem; font-weight: 650; }
.t-reason-label { font-size: .82rem; color: #b6c2d4; margin-top: .2rem; }
.t-reason-rate { font-size: .74rem; color: #8ba0bb; margin-top: .25rem; }
.t-outcome { padding: .12rem .5rem; border-radius: 6px; font-size: .76rem; }
.t-outcome-done { background: rgba(52,211,153,.14); color: #6ee7b7; }
.t-outcome-dismissed { background: rgba(248,113,113,.14); color: #fca5a5; }
.t-outcome-snoozed { background: rgba(251,191,36,.14); color: #fcd34d; }
.t-note { color: #9fb0c6; background: #10151f; border: 1px dashed #2b3a52; border-radius: 12px; padding: 1rem 1.15rem; font-size: .9rem; }
.t-foot { color: #6f7f97; font-size: .78rem; line-height: 1.55; margin-top: 1.5rem; border-top: 1px solid #1f2937; padding-top: 1rem; }
`
