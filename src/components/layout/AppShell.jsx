import { Button } from '../shared/Button.jsx'
import { navIcons } from './navIcons.jsx'
import { ErrorBoundary } from '../shared/ErrorBoundary.jsx'
import { LANGUAGES, useI18n } from '../../lib/i18n/index.js'

/**
 * Navigation, grouped by the question the manager is asking.
 *
 * A flat list of twelve engine names told nobody what any screen was for. The
 * groups below are phrased as jobs — daily work, market, shelves, inventory —
 * and every entry carries a one-line hint under its name for the same reason.
 *
 * All labels are keys, not strings: the app runs in Arabic, Hebrew or English.
 *
 * The old score-ranked Planogram page stays ABSENT (task D-6). Measured against
 * real data it put all 7,451 products on the bottom shelf with 2 facings each.
 * `store-layout` and `shelf-plan` replace it.
 */
/**
 * The ten V1 pages (design §20.1: "nav reduced to 10 items"), grouped as the owner would
 * group them rather than as the codebase does.
 *
 * The V2/V4 entries — reorder, approved orders, assortment gaps, store layout, shelf plan,
 * dashboard, report — are gone from here at the cut-over. Their code stays until Phase 4 so
 * a rollback still has somewhere to land; it is simply no longer reachable.
 */
const navGroups = [
  {
    id: 'group.daily',
    items: [
      { id: 'daily' },
      { id: 'questions' },
    ],
  },
  {
    id: 'group.market',
    items: [
      { id: 'price_consistency' },
      { id: 'competitor_position' },
    ],
  },
  {
    id: 'group.inventory',
    items: [
      { id: 'reconciliation' },
      { id: 'hygiene' },
      { id: 'catalogue_lifecycle' },
      { id: 'margin_below_cost' },
      { id: 'receiving' },
    ],
  },
  {
    id: 'group.system',
    items: [{ id: 'data' }],
  },
]

/**
 * The icon for a nav id, or nothing.
 *
 * Falling back to `null` rather than a placeholder glyph is deliberate: a
 * missing icon should leave a quiet gap, not print a stray letter — which is
 * exactly the failure this set was written to remove.
 */
function renderNavIcon(id) {
  const Icon = navIcons[id]
  return Icon ? <Icon /> : null
}

export function AppShell({
  activePage,
  children,
  dataProvenance,
  hasDemoState = false,
  onNavigate,
  onResetDemoState,
}) {
  const { t, language, setLanguage } = useI18n()
  const catalogIsReal = dataProvenance?.catalog === 'real'
  const competitorIsReal = dataProvenance?.competitor === 'real'

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark">SS</div>
          <div>
            <p className="brand-title">{t('app.name')}</p>
            <p className="brand-subtitle">{t('app.tagline')}</p>
          </div>
        </div>

        <nav className="sidebar-nav" aria-label={t('app.nav')}>
          {navGroups.map((group) => (
            <div className="nav-group" key={group.id}>
              <p className="nav-group-label">{t(group.id)}</p>
              {group.items.map((item) => {
                const isActive = activePage === item.id
                return (
                  <button
                    key={item.id}
                    type="button"
                    aria-current={isActive ? 'page' : undefined}
                    className={`nav-item ${isActive ? 'nav-item-active' : ''}`}
                    onClick={() => onNavigate(item.id)}
                  >
                    <span className="nav-icon">{renderNavIcon(item.id)}</span>
                    <span className="nav-item-text">
                      <span className="nav-item-name">{t(`page.${item.id}.name`)}</span>
                      {/* The hint is why anyone would open this screen. Without it
                          a name like "Gaps" or "Overview" is a guess. */}
                      <span className="nav-item-hint">{t(`page.${item.id}.hint`)}</span>
                    </span>
                  </button>
                )
              })}
            </div>
          ))}
        </nav>

        <div className="sidebar-foot">
          <label className="lang-switch">
            <span className="lang-switch-label">{t('app.language')}</span>
            <select
              aria-label={t('app.language')}
              className="lang-switch-select"
              onChange={(event) => setLanguage(event.target.value)}
              value={language}
            >
              {Object.values(LANGUAGES).map((entry) => (
                <option key={entry.code} value={entry.code}>
                  {entry.label}
                </option>
              ))}
            </select>
          </label>

          {hasDemoState && (
            <Button className="sidebar-reset-btn" onClick={onResetDemoState} tone="ghost">
              {t('app.resetDemo')}
            </Button>
          )}
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div>
            <h1>{t(`page.${activePage}.title`)}</h1>
            <p className="page-description">{t(`page.${activePage}.description`)}</p>
          </div>

          <div className="topbar-meta" aria-label={t('provenance.realPos')}>
            <span className={`pill ${catalogIsReal ? 'pill-success' : ''}`}>
              {catalogIsReal ? t('provenance.realPos') : t('provenance.demo')}
            </span>
            {competitorIsReal && <span className="pill pill-success">{t('provenance.realPrices')}</span>}
            <span className="pill">{t('provenance.poc')}</span>
          </div>
        </header>

        <ErrorBoundary key={activePage}>
          <div className="page-body">{children}</div>
        </ErrorBoundary>
      </main>
    </div>
  )
}
