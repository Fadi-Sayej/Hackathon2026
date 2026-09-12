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
  const { t } = useI18n()
  const capability = artefact?.capabilities?.[capabilityId]

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

  const { status, unavailable_reason: reason, counts, thresholds, entries } = capability

  return (
    <section className="capability" data-capability={capabilityId} {...dirProps()}>
      <h2>{t(`capability.${capabilityId}`)}</h2>

      {status === 'unavailable' ? (
        // AC-107. No counts are rendered at all: a zero here would be read as a finding,
        // and the capability did not run.
        <p className="capability__unavailable">{t(`unavailable.${reason}`)}</p>
      ) : (
        <>
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
                  <dd>{Array.isArray(value) ? value.length : String(value)}</dd>
                </div>
              ))}
            </dl>
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
