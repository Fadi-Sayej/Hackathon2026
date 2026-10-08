import { unavailableReason } from '../lib/i18n/unavailableReason.js'
import { formatWindowId } from '../lib/i18n/formatPeriod.js'
import { useI18n } from '../lib/i18n/index.js'
import { dirProps } from '../lib/utils/rtl.js'

/**
 * One capability, whole. Six routes share this component: price, reconciliation, hygiene,
 * competitor, catalogue and margin.
 *
 * This is where AC-110 is discharged — the full set per capability stays reachable away
 * from the daily surface. The ten-entry bound is a property of the surface, not of the
 * data, so nothing here is truncated.
 *
 * margin_below_cost renders here and is *not* selected by compose: no specification
 * produces it, so it is browse-only until SPEC-008 exists (SPEC-GAP-A).
 */
export function CapabilityPage({ artefact, capabilityId }) {
  const { t, language } = useI18n()
  const capability = artefact?.capabilities?.[capabilityId]
  // A threshold in words: yes or no, and a method's name as what it means (F6 AC-112).
  const thresholdText = (value) => {
    if (Array.isArray(value)) return String(value.length)
    if (typeof value === 'boolean') return t(value ? 'common.yes' : 'common.no')
    if (typeof value === 'string') return t(`threshold.value.${value}`)
    return String(value)
  }

  if (!capability) {
    // An absent capability is not an empty one. Rendering nothing would read as "no
    // findings", which is a claim this page cannot support.
    return (
      <section className="capability capability__missing" {...dirProps()}>
        <h2>{t(`capability.${capabilityId}`)}</h2>
        <p>{t('capability.missing')}</p>
      </section>
    )
  }

  const { status, unavailable_reason: reason, counts, thresholds, entries, notes, window } = capability
  // ADR-043: F3's breaches wait for the owner's price rule (D-39) while the rest of F3 goes on. The
  // loader folds them in (foldPolicyBreach), and says here what they wait for when they cannot run.
  const waiting = capability.waiting_for
  // F4 AC-067: a dead count on a short window is stated with that window and its seasonal limit.
  const seasonal = (notes || []).includes('seasonal_misclassification_possible') && window?.window_id

  return (
    <section className="capability" data-capability={capabilityId} {...dirProps()}>
      <h2>{t(`capability.${capabilityId}`)}</h2>

      {status === 'unavailable' ? (
        // AC-107. No counts are rendered at all: a zero here would be read as a finding,
        // and the capability did not run.
        <p className="capability__unavailable">{unavailableReason(t, reason)}</p>
      ) : (
        <>
          {seasonal ? (
            <p className="capability__note">
              {t('capability.note.seasonal', { period: formatWindowId(window.window_id, t, language) })}
            </p>
          ) : null}

          <dl className="capability__counts">
            {Object.entries(counts || {}).map(([name, value]) => (
              <div key={name}>
                <dt>{t(`count.${name}`)}</dt>
                {/* A null count is "undetermined", never zero (D-3) */}
                <dd>{value === null ? t('count.undetermined') : String(value)}</dd>
              </div>
            ))}
          </dl>

          {thresholds && Object.keys(thresholds).length > 0 ? (
            // F7-S1 / ARCH-DRIVER-007: a count is rendered with the thresholds that
            // governed it, or a reader cannot tell what it was measured against.
            <dl className="capability__thresholds">
              {Object.entries(thresholds).map(([name, value]) => (
                <div key={name}>
                  <dt>{t(`threshold.${name}`)}</dt>
                  <dd data-text={typeof value === 'string' ? '' : undefined}>{thresholdText(value)}</dd>
                </div>
              ))}
            </dl>
          ) : null}

          {waiting ? (
            <p className="capability__unavailable capability__waiting">{unavailableReason(t, waiting)}</p>
          ) : null}

          <ol className="capability__entries">
            {(entries || []).map((entry) => (
              <li key={entry.id} data-entry-id={entry.id}>
                <span className="capability__product">{entry.product_name || entry.barcode}</span>
                <span className="capability__what">{t(`characterisation.${entry.characterisation}`)}</span>
              </li>
            ))}
          </ol>
        </>
      )}
    </section>
  )
}
