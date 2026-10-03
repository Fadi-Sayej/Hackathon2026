import { LANGUAGES, useI18n } from '../lib/i18n/index.js'
import './auth.css'

/**
 * The signed-out screen (the sign-in page, 2026-10-03): a welcome, not the app with its nav
 * taken out. The brand and what SmartShelf does on one side, the sign-in card on the other;
 * on a phone, one above the other. The language switch stays: it may be needed before signing in.
 */
const POINTS = ['auth.welcome.today', 'auth.welcome.prices', 'auth.welcome.orders']

export function SignInLayout({ children }) {
  const { t, language, setLanguage } = useI18n()
  return (
    <div className="signin">
      <aside className="signin__brand">
        <div className="brand-block">
          <div className="brand-mark">SS</div>
          <div>
            <p className="brand-title">{t('app.name')}</p>
            <p className="brand-subtitle">{t('app.tagline')}</p>
          </div>
        </div>
        <div className="signin__pitch">
          <p className="signin__headline">{t('auth.welcome.headline')}</p>
          <ul className="signin__points">
            {POINTS.map((key) => <li key={key}>{t(key)}</li>)}
          </ul>
        </div>
        <label className="lang-switch signin__lang">
          <span className="lang-switch-label">{t('app.language')}</span>
          <select aria-label={t('app.language')} className="lang-switch-select" value={language}
            onChange={(event) => setLanguage(event.target.value)}>
            {Object.values(LANGUAGES).map((entry) => <option key={entry.code} value={entry.code}>{entry.label}</option>)}
          </select>
        </label>
      </aside>
      <main className="signin__main">{children}</main>
    </div>
  )
}
