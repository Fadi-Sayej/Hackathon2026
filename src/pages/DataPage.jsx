import { useI18n } from '../lib/i18n/index.js'
import { dirProps } from '../lib/utils/rtl.js'

/**
 * The page an operator opens when a number looks wrong.
 *
 * It answers three questions and nothing else: how old is the evidence, what could the run
 * not do, and which capability is not speaking. Every one of those is already in the
 * artefact; this page's whole job is to stop them being invisible.
 */

/** A vintage that is absent reads as absent. A blank cell reads as an oversight. */
function Field({ id, label, children, empty }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd data-field={id}>{children ?? empty}</dd>
    </div>
  )
}

export function DataPage({ artefact }) {
  const { t } = useI18n()
  if (!artefact) return null

  const { vintages = {}, run = {}, capabilities = {} } = artefact
  const sales = vintages.sales || {}
  const none = t('data.none')

  // ADR-017. The engine does not publish this yet. Rendering "yes" in its absence would
  // assert something the artefact cannot support — the one thing this page exists to stop.
  const imported = sales.imported_this_run
  const importedLabel = imported === undefined || imported === null
    ? t('data.unknown')
    : t(imported ? 'common.yes' : 'common.no')

  // Which step to blame is derivable, so derive it rather than making the reader scan.
  const cause = run.status === 'partial'
    ? (run.steps || []).find((s) => s.status === 'error')
    : run.status === 'degraded'
      ? (run.steps || []).find((s) => s.status === 'degraded' || s.status === 'skipped')
      : null

  return (
    <section className="data" {...dirProps()}>
      <h2>{t('data.title')}</h2>

      <p className="data__run" data-run-status={run.status}>
        {t(`data.run.${run.status}`)}
      </p>
      {cause ? (
        <p className="data__cause">
          {cause.step}{cause.error ? ` — ${cause.error}` : ''}
        </p>
      ) : null}

      <dl className="data__vintages">
        {/* The date alone is not provenance. `file_mtime` on a CI runner is the checkout
            time, not the day the export was taken, so a bare date there reads as "this
            morning" when the stock counts can be months old. Only `declared` is certainly
            the export date; the other two say what they actually are. */}
        <Field id="pos" label={t('data.pos')} empty={none}>
          {vintages.pos?.as_of
            ? [vintages.pos.as_of,
               vintages.pos.as_of_source && vintages.pos.as_of_source !== 'declared'
                 ? t(`data.pos.${vintages.pos.as_of_source}`)
                 : null,
              ].filter(Boolean).join(' · ')
            : null}
        </Field>
        <Field id="sales_window" label={t('data.salesWindow')} empty={none}>
          {sales.first && sales.last ? `${sales.first} … ${sales.last}` : null}
        </Field>
        <Field id="imported_this_run" label={t('data.importedThisRun')} empty={none}>
          {importedLabel}
        </Field>
        <Field id="competitor" label={t('data.competitor')} empty={none}>
          {vintages.competitor?.snapshot_date}
        </Field>
        {/* `from_mirror` means the engine could not reach Firestore and replayed the
            committed replica instead. Without saying so, this line reads "available" under
            a timestamp that belongs to whoever last ran with a credential — which is
            exactly what the pilot would show if FIREBASE_SERVICE_ACCOUNT_JSON were ever
            unset in CI. Design §13: unavailable honestly, never silently local. */}
        <Field id="owner_state" label={t('data.ownerState')} empty={none}>
          {vintages.owner_state
            ? [
                t(`data.ownerState.${vintages.owner_state.status}`),
                vintages.owner_state.reason === 'from_mirror' ? t('data.ownerState.fromMirror') : null,
                vintages.owner_state.pulled_at,
              ]
                .filter(Boolean)
                .join(' · ')
            : null}
        </Field>
      </dl>

      <ul className="data__capabilities">
        {Object.entries(capabilities).map(([id, capability]) => (
          <li key={id} data-capability-status={id}>
            {t(`capability.${id}`)} — {capability.status === 'unavailable'
              ? t(`unavailable.${capability.unavailable_reason}`)
              : t('data.available')}
          </li>
        ))}
      </ul>
    </section>
  )
}
