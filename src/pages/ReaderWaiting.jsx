import { useI18n } from '../lib/i18n/index.js'
import { useDates } from './shelfCommon.js'

/**
 * F12-S1 FR-223 (D-34): the shelf reader has read widths from his photos, and they wait for its
 * acceptance run. Said at the top of Store layout and under the plan's conditions on Shelf plan,
 * in the words the repository owner approved on 2026-10-06. Nothing is said once the run has
 * passed, or before the reader has read anything: those products are then placed, or listed
 * as without a width, as they already are.
 */
export function ReaderWaiting({ reader }) {
  const { t } = useI18n()
  const { date } = useDates()
  if (reader?.status !== 'waiting_for_acceptance') return null
  const acceptance = reader.acceptance || {}
  return (
    <p className="plan__conditions" data-reader="waiting_for_acceptance">
      {t('layout.reader.waiting', {
        n: reader.widths, date: date(reader.read_on), min: acceptance.minimum, tol: acceptance.tolerance_mm,
        within: acceptance.within, listed: acceptance.listed,
      })}
    </p>
  )
}
