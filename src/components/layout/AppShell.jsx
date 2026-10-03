import { useState } from 'react'
import { Button } from '../shared/Button.jsx'
import { navIcons } from './navIcons.jsx'
import { navGroups } from './navGroups.js'
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
  notice = null,
  children,
  dataProvenance,
  hasDemoState = false,
  onNavigate,
  onResetDemoState,
}) {
  // Which collapsible nav groups the owner has opened. Closed is the default: the findings
  // group is six capability pages he reaches deliberately, not daily work.
  const [openGroups, setOpenGroups] = useState(() => new Set())
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
          {navGroups.map((group) => {
            // A collapsible group opens itself when the active page is inside it, so landing
            // on one of its pages never shows a closed drawer with no explanation — and the
            // owner's own toggle wins for every other group state.
            const holdsActive = group.items.some((item) => item.id === activePage)
            const isOpen = !group.collapsible || holdsActive || openGroups.has(group.id)
            return (
            /* `data-collapsed` rather than not rendering: on a phone the nav is a single
               scrolling bar with `.nav-group { display: contents }` and every group label
               hidden, so a JS-collapsed group would be shut with no way to open it and its
               six pages would be unreachable on the device the owner actually uses. The
               items are always in the DOM; CSS hides them, and only above 900px. */
            <div
              className="nav-group"
              key={group.id}
              data-collapsible={group.collapsible || undefined}
              data-collapsed={group.collapsible && !isOpen ? 'true' : undefined}
            >
              {group.collapsible ? (
                <button
                  type="button"
                  className="nav-group-label nav-group-toggle"
                  aria-expanded={isOpen}
                  data-nav-group={group.id}
                  onClick={() => setOpenGroups((open) => {
                    const next = new Set(open)
                    if (next.has(group.id)) next.delete(group.id)
                    else next.add(group.id)
                    return next
                  })}
                >
                  {t(group.id)}
                  <span className="nav-group-caret" aria-hidden="true">{isOpen ? '\u2212' : '+'}</span>
                </button>
              ) : (
                <p className="nav-group-label">{t(group.id)}</p>
              )}
              {group.items.map((item) => {
                const isActive = activePage === item.id
                return (
                  <button
                    key={item.id}
                    type="button"
                    aria-current={isActive ? 'page' : undefined}
                    className={`nav-item ${isActive ? 'nav-item-active' : ''}`}
                    /* The page id, in the DOM, because the label is translated and the
                       order is a layout choice — neither is a stable handle. Same role as
                       `data-field` on the data page. e2e/v1-navigation.spec.js reads the
                       nav from here rather than from a list it keeps in step by hand. */
                    data-nav={item.id}
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
            )
          })}
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
        {notice}
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
