import { Button } from '../shared/Button.jsx'
import { ErrorBoundary } from '../shared/ErrorBoundary.jsx'

// Ordered by what a store manager should look at first. "Today" is the home screen.
//
// Planogram is deliberately ABSENT (task D-6). Measured against real data it put all
// 7,451 products on the bottom shelf with 2 facings each, because 45% of its score is
// sales velocity we do not have and its category rules are hardcoded English against
// Hebrew categories. The page still exists in the repo; it comes back when velocity is
// real and someone has measured YomYom's actual shelves.
const navItems = [
  { id: 'operational', label: 'Today', icon: '!' },
  { id: 'prices', label: 'Prices', icon: '₪' },
  { id: 'assortment', label: 'Gaps', icon: '◫' },
  { id: 'expiry', label: 'Expiry', icon: 'E' },
  { id: 'products', label: 'Products', icon: 'P' },
  { id: 'dashboard', label: 'Overview', icon: 'D' },
  { id: 'recommendations', label: 'Reorder', icon: 'R' },
  { id: 'report', label: 'AI Report', icon: 'A' },
  { id: 'orders', label: 'Approved Orders', icon: 'O' },
  { id: 'data-source', label: 'Data Source', icon: 'C' },
]

export function AppShell({
  activePage,
  children,
  dataProvenance,
  hasDemoState = false,
  onNavigate,
  onResetDemoState,
  pageMeta,
}) {
  const catalogIsReal = dataProvenance?.catalog === 'real'
  const competitorIsReal = dataProvenance?.competitor === 'real'
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark">SS</div>
          <div>
            <p className="brand-title">SmartShelf AI</p>
            <p className="brand-subtitle">Retail AI Operations</p>
          </div>
        </div>

        <nav className="sidebar-nav" aria-label="Main navigation">
          {navItems.map((item) => {
            const isActive = activePage === item.id
            return (
              <button
                key={item.id}
                type="button"
                aria-current={isActive ? 'page' : undefined}
                className={`nav-item ${isActive ? 'nav-item-active' : ''}`}
                onClick={() => onNavigate(item.id)}
              >
                <span className="nav-icon" aria-hidden="true">
                  {item.icon}
                </span>
                <span>{item.label}</span>
              </button>
            )
          })}
        </nav>

        <div className="sidebar-card">
          <p className="sidebar-card-eyebrow">Demo mode</p>
          <h2>POC Demo</h2>
          <p>Local-first data and deterministic retail logic.</p>
          {hasDemoState && (
            <Button className="sidebar-reset-btn" onClick={onResetDemoState} tone="ghost">
              Reset demo state
            </Button>
          )}
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div>
            <p className="eyebrow">SmartShelf AI</p>
            <h1>{pageMeta.title}</h1>
            <p className="page-description">{pageMeta.description}</p>
          </div>

          <div className="topbar-meta" aria-label="Data status">
            <span className={`pill ${catalogIsReal ? 'pill-success' : ''}`}>
              {catalogIsReal ? 'Real POS data' : 'Demo data'}
            </span>
            <span className={`pill ${competitorIsReal ? 'pill-success' : ''}`}>
              {competitorIsReal ? 'Real competitor prices' : 'No competitor data'}
            </span>
            <span className="pill">POC</span>
          </div>
        </header>

        <ErrorBoundary key={activePage}>
          <div className="page-body">{children}</div>
        </ErrorBoundary>
      </main>
    </div>
  )
}
