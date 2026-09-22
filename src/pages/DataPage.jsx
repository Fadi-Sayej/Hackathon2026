import { unavailableReason } from '../lib/i18n/unavailableReason.js'
import { useI18n } from '../lib/i18n/index.js'
import { dirProps } from '../lib/utils/rtl.js'
import { deferredEntries } from '../surface/compose.js'

/** Vintage sources a human wrote down, as opposed to the two the importer infers. */
const DECLARED_VINTAGE = new Set(['declared', 'declared_sidecar'])

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

export function DataPage({ artefact, ownerState, onRestore, now }) {
  const { t } = useI18n()
  if (!artefact) return null

  /**
   * Entries the owner hid with "Later" and has not got back.
   *
   * It lives here rather than on the daily surface because FR-102 says so: "The owner MUST
   * be able to reach the full set of entries for a capability deliberately, on a surface
   * other than this one." Putting it on the daily surface would also collide with AC-101,
   * which forbids a count of unshown entries there — FR-101's reason being that the ten-item
   * bound exists to make the day finishable, and showing the remainder undoes it.
   *
   * Before #142 "Later" carried no date and `compose` reads a dateless deferral as
   * indefinite, so one tap hid an entry permanently. #142 gave the surface an Undo for the
   * tap just made; this is the way back for everything already hidden.
   */
  // `now` comes from App, which fixes it once per session. Reading the clock here would be
  // an impure render — and would also mean a deferral could lapse mid-render, so the list
  // shortened itself while the owner was looking at it.
  const hidden = deferredEntries(artefact, ownerState, { now })

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
               // Both declared forms are a date a person wrote down, so neither needs a
               // caveat. The other two are proxies that have each been wrong in
               // production — mtime is reset by `git clone`, and `git log` answers with
               // the checkout commit in a shallow one — so they say what they are.
               DECLARED_VINTAGE.has(vintages.pos.as_of_source)
                 ? null
                 : vintages.pos.as_of_source
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
        {/* ADR-021. It exists so Task 4.3's precondition can be checked instead of guessed,
            and the wording is part of the decision: these are browsers that HAVE saved, not
            the devices that exist. Absent reads as empty, never as zero — nobody having
            saved and nobody having registered are different facts. */}
        <Field id="owner_devices" label={t('data.devices')} empty={none}>
          {vintages.owner_state?.devices?.status === 'available'
            ? t('data.devices.counted', {
              n: vintages.owner_state.devices.count,
              last: vintages.owner_state.devices.last_seen_at.at(-1) ?? '—',
            })
            : null}
        </Field>
      </dl>

      {hidden.length > 0 && onRestore ? (
        <section className="data__hidden" aria-label={t('data.hidden.title')}>
          <h3>{t('data.hidden.title')}</h3>
          <p className="data__hidden-why">{t('data.hidden.why')}</p>
          <ul className="data__hidden-list">
            {hidden.map(({ entry, at }) => (
              <li key={entry.id} data-hidden-entry={entry.id}>
                <span className="data__hidden-name" {...dirProps(entry.product_name)}>
                  {entry.product_name || entry.barcode || entry.id}
                </span>
                {/* The date it was hidden, because "Restore" with no context asks the owner
                    to remember a tap he may have made a fortnight ago. */}
                <span className="data__hidden-when">
                  {at ? new Date(at).toLocaleDateString() : t('data.none')}
                </span>
                <button type="button" className="data__hidden-restore"
                  data-restore={entry.id} onClick={() => onRestore(entry.id)}>
                  {t('data.hidden.restore')}
                </button>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <ul className="data__capabilities">
        {Object.entries(capabilities).map(([id, capability]) => (
          <li key={id} data-capability-status={id}>
            {t(`capability.${id}`)} — {capability.status === 'unavailable'
              ? unavailableReason(t, capability.unavailable_reason)
              : t('data.available')}
          </li>
        ))}
      </ul>
    </section>
  )
}
