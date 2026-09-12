import { useT } from '../lib/i18n/index.js'
import { ReceivingCaptureForm } from '../components/receiving/ReceivingCaptureForm.jsx'

/**
 * Receiving — capture only (design §20.1).
 *
 * The expiry summary that used to sit above this form is gone, and not for tidiness. Every
 * bucket it rendered reads zero: `operational.json` carries `expired: 0, critical_7d: 0,
 * warning_14d: 0, upcoming_30d: 0` and `totalScans: 0`, because no receipts have been
 * recorded yet. F10's intent says so plainly — it needs thirty days of recorded receipts
 * that do not exist.
 *
 * Five cards reading zero do not say "nothing has been recorded". They say "we looked, and
 * there is nothing expiring", which is a measurement nobody took. D-3: where a figure
 * cannot be stated honestly the surface shows no figure.
 *
 * The summary returns when there is something to summarise — the counter starts on the day
 * the owner's staff begin recording, which is what this form is for.
 */
export function ReceivingPage() {
  const t = useT()

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">{t('exp.receivingEyebrow')}</p>
          <h2>{t('exp.recordTitle')}</h2>
        </div>
      </div>
      <p className="page-description">
        {t('exp.receivingDesc1')} <strong>{t('exp.expiryOnlyMode')}</strong>{' '}
        {t('exp.receivingDesc2')}
      </p>

      <ReceivingCaptureForm products={[]} />
    </section>
  )
}
