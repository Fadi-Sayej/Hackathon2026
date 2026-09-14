/**
 * The one place that turns an engine `unavailable_reason` into owner-readable text.
 *
 * The reason code is domain vocabulary — the engine decides it, the artefact carries
 * it unchanged, and it is never translated on that side. Only this layer knows what
 * it says to a person, which is why the mapping lives in the dictionaries and the
 * lookup lives here rather than being repeated at each of the three render sites
 * (DailyPage, CapabilityPage, DataPage).
 *
 * WHY THERE IS A FALLBACK
 *   `createTranslator` returns the key itself on a miss — deliberately, so an
 *   untranslated string is visible rather than blank. That is the right default for a
 *   label a developer will notice. It is the wrong default here: this text is read by
 *   the store owner on the one day a capability could not run, and
 *   `unavailable.no_pos_data` tells him nothing. Eight of the nine reasons the engine
 *   can emit had no translation at all until #103.
 *
 *   So an unknown reason degrades to a sentence rather than to an identifier. It is
 *   still worse than a specific answer — hence the test that every reason the engine
 *   can actually emit has one.
 */

/** Rendered when the reason is absent, or is one this build has no words for. */
export const UNKNOWN_REASON_KEY = 'unavailable.unknown'

/**
 * @param {(key: string) => string} t  translator from useI18n()
 * @param {string|null|undefined} reason  `unavailable_reason` as the artefact carries it
 */
export function unavailableReason(t, reason) {
  if (!reason) return t(UNKNOWN_REASON_KEY)
  const key = `unavailable.${reason}`
  const text = t(key)
  // The translator echoes the key when it has no entry; that is the miss signal.
  return text === key ? t(UNKNOWN_REASON_KEY) : text
}
