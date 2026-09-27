import { useCallback, useEffect, useState } from 'react'

import { loadMeasurement } from '../lib/dataAdapters/loadMeasurement.js'
import { formatDate, formatShekel } from '../lib/utils/format.js'
import { viewMeasurement } from './telemetryModel.js'

// The team's measurement page (F13-S1, Phase 4 Task 4.5). It renders what the engine published
// in public/data/measurement.json and computes nothing (ADR-023, ADR-001). The file is its own,
// beside dashboard.json, so the edge gate keeps it from the owner (ADR-029 Decision 6).

const pct = (share) => (share == null ? '—' : `${Math.round(share * 100)}%`)
const n = (value) => value.toLocaleString('en-US')

function Metric({ label, value, detail, tone = 'neutral' }) {
  return (
    <div className={`t-card t-card-${tone}`}>
      <div className="t-card-label">{label}</div>
      <div className="t-card-value">{value}</div>
      {detail ? <div className="t-card-detail">{detail}</div> : null}
    </div>
  )
}

function Bar({ share }) {
  return (
    <div className="t-bar">
      <div className="t-bar-fill" style={{ width: `${Math.round((share ?? 0) * 100)}%` }} />
    </div>
  )
}

function Measurement({ view }) {
  const { totals } = view
  return (
    <>
      <section className="t-grid">
        <Metric label="Shown in this run" value={n(totals.shown)}
          detail={`entries published ${formatDate(view.generatedAt)}`} tone="info" />
        <Metric label="Decided" value={n(totals.decided)}
          detail={`${totals.acted} acted on · ${totals.declined} dismissed · ${totals.deferred} deferred`} />
        <Metric label="Acted on" value={n(totals.acted)}
          detail={view.nothingDecided ? 'nothing decided yet' : `${pct(view.actedShare)} of decided`}
          tone={totals.acted ? 'good' : 'neutral'} />
      </section>

      {view.nothingDecided ? (
        <p className="t-note">
          No decisions recorded yet. When the owner acts on, dismisses or defers an entry, it is
          counted here the next night.
        </p>
      ) : null}

      <section className="t-panel">
        <h2>Money recovered</h2>
        <p className="t-panel-sub">
          Only from entries the owner acted on, at the value the engine published when he decided.
          One row per kind and certainty: they are never added together.
        </p>
        {view.money.length === 0 ? (
          <p className="t-panel-sub">No acted-on decision carries money yet.</p>
        ) : view.money.map((row) => (
          <div className="t-money" key={`${row.kind}|${row.certainty}`} data-money={`${row.kind}|${row.certainty}`}>
            <span>{row.kind === 'per_sale' ? 'per sale' : row.kind} · {row.certainty} · from {row.decisions} acted-on decision{row.decisions === 1 ? '' : 's'}</span>
            <strong>{formatShekel(row.amount)}</strong>
          </div>
        ))}
      </section>

      <section className="t-panel">
        <h2>Which alert types earn their place</h2>
        <p className="t-panel-sub">
          What this run shows of each type, and what the owner decided about it. The share is of
          his decisions only: a run&apos;s entries and his decisions are different sets.
        </p>
        <table className="t-table">
          <thead>
            <tr>
              <th>Type</th>
              <th className="t-num">Shown</th>
              <th className="t-num">Acted on</th>
              <th className="t-num">Dismissed</th>
              <th className="t-num">Deferred</th>
              <th className="t-num">Not in this run</th>
              <th className="t-accept">Acted on, of decided</th>
            </tr>
          </thead>
          <tbody>
            {view.families.map((row) => (
              <tr key={row.family} data-family={row.family}>
                <td><span className="t-type">{row.family}</span></td>
                <td className="t-num">{n(row.shown)}</td>
                <td className="t-num">{row.acted}</td>
                <td className="t-num">{row.declined}</td>
                <td className="t-num">{row.deferred}</td>
                <td className="t-num t-muted">{row.notInThisRun}</td>
                <td className="t-accept">
                  <div className="t-accept-cell">
                    <Bar share={row.actedShare} />
                    <span>{pct(row.actedShare)}</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="t-panel">
        <h2>Why alerts were dismissed</h2>
        <p className="t-panel-sub">
          A tool that is confidently wrong is worse than no tool, so “the data is wrong” is the
          dismissal to watch.
        </p>
        <div className="t-reasons">
          {view.reasons.map((r) => (
            <div className="t-reason" key={r.reason}>
              <div className="t-reason-count">{r.count}</div>
              <div className="t-reason-label">{r.label}</div>
              {r.reason === 'wrong_data' ? (
                <div className="t-reason-rate">
                  {view.wrongDataShare == null ? 'no dismissals yet' : `${pct(view.wrongDataShare)} of dismissals`}
                </div>
              ) : null}
            </div>
          ))}
        </div>
      </section>

      <footer className="t-foot">
        <p>
          “Shown” is the run published {formatDate(view.generatedAt)}. Decisions are every one the
          owner recorded
          {view.window.first ? `, ${formatDate(view.window.first)} to ${formatDate(view.window.last)}` : ''},
          as the engine read them {formatDate(view.window.pulled_at)}
          {view.devices != null ? `, from ${view.devices} devices` : ''}. A decision whose entry
          this run no longer shows is counted under “not in this run”, never dropped. ₪ figures are
          per sale, deliberately not multiplied by volume: the stock counts are unreliable, so a
          lot value would be a guess dressed up as a number.
        </p>
      </footer>
    </>
  )
}

export function TelemetryDashboard({ load = loadMeasurement }) {
  const [result, setResult] = useState(null)
  const reload = useCallback(() => {
    let cancelled = false
    load().then((next) => { if (!cancelled) setResult(next) })
    return () => { cancelled = true }
  }, [load])
  useEffect(() => reload(), [reload])

  const view = result?.status === 'ok' ? viewMeasurement(result.body) : null

  return (
    <div className="t-root">
      <style>{STYLES}</style>

      <header className="t-header">
        <div>
          <p className="t-eyebrow">SmartShelf · Pilot measurement</p>
          <h1>Did the alerts help?</h1>
          <p className="t-sub">
            Internal view for the team. What the engine&apos;s latest run shows, and every decision
            the owner recorded, as the engine published them.
          </p>
        </div>
        <div className="t-source">
          {view?.generatedAt ? `Measured ${formatDate(view.generatedAt)}` : 'measurement.json'}
          <button className="t-reload" onClick={reload}>Reload</button>
          {/* ADR-029 §3: team accounts land here after sign-in; this is the way to the owner's
              app, which they see read-only. */}
          <a className="t-reload" href="/">Open the owner&apos;s app</a>
        </div>
      </header>

      {result === null ? (
        <p className="t-note">Loading the measurement…</p>
      ) : result.status === 'missing' ? (
        <p className="t-note">
          The measurement has not been published yet. The nightly run writes it beside the
          artefact.
        </p>
      ) : result.status !== 'ok' ? (
        <p className="t-note">The measurement could not be loaded: {result.reason}.</p>
      ) : view.state === 'unavailable' ? (
        <p className="t-note">
          The engine could not measure this run: {view.reason ?? 'no reason was published'}. No
          number is shown in its place.
        </p>
      ) : (
        <Measurement view={view} />
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
.t-reload { margin-left: .5rem; background: #1c2635; color: #cdd7e6; border: 1px solid #33415a;
  border-radius: 7px; padding: .3rem .6rem; cursor: pointer; font-size: .8rem; }
.t-reload:hover { background: #24324a; }
a.t-reload { display: inline-block; text-decoration: none; }
.t-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: .9rem; margin-bottom: 1.75rem; }
.t-card { background: #141b27; border: 1px solid #232f42; border-radius: 12px; padding: 1rem 1.1rem; }
.t-card-good { border-color: #2f6b52; }
.t-card-info { border-color: #2b4a6b; }
.t-card-label { font-size: .78rem; color: #8ba0bb; margin-bottom: .4rem; }
.t-card-value { font-size: 1.7rem; font-weight: 650; }
.t-money { display: flex; justify-content: space-between; gap: 1rem; padding: .55rem 0; border-bottom: 1px solid #171f2b; font-size: .92rem; }
.t-money strong { font-size: 1.15rem; font-variant-numeric: tabular-nums; }
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
.t-accept-cell { display: flex; align-items: center; gap: .55rem; min-width: 130px; }
.t-bar { flex: 1; height: 7px; background: #1c2636; border-radius: 4px; overflow: hidden; }
.t-bar-fill { height: 100%; background: linear-gradient(90deg, #38bdf8, #34d399); }
.t-reasons { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: .8rem; }
.t-reason { background: #141b27; border: 1px solid #232f42; border-radius: 11px; padding: .9rem 1rem; }
.t-reason-count { font-size: 1.5rem; font-weight: 650; }
.t-reason-label { font-size: .82rem; color: #b6c2d4; margin-top: .2rem; }
.t-reason-rate { font-size: .74rem; color: #8ba0bb; margin-top: .25rem; }
.t-note { color: #9fb0c6; background: #10151f; border: 1px dashed #2b3a52; border-radius: 12px; padding: 1rem 1.15rem; font-size: .9rem; }
.t-foot { color: #6f7f97; font-size: .78rem; line-height: 1.55; margin-top: 1.5rem; border-top: 1px solid #1f2937; padding-top: 1rem; }
`
