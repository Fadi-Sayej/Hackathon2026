import { Button } from '../shared/Button.jsx'
import { ErrorBoundary } from '../shared/ErrorBoundary.jsx'

const navItems = [
  { id: 'dashboard', label: 'Dashboard', icon: 'D' },
  { id: 'products', label: 'Products', icon: 'P' },
  { id: 'recommendations', label: 'Recommendations', icon: 'R' },
  { id: 'planogram', label: 'Planogram', icon: 'S' },
  { id: 'orders', label: 'Approved Orders', icon: 'O' },
  { id: 'data-source', label: 'Data Source', icon: 'C' },
]

export function AppShell({
  activePage,
  children,
  hasDemoState = false,
  onNavigate,
  onResetDemoState,
  pageMeta,
}) {
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

          <div className="topbar-meta" aria-label="Demo status">
            <span className="pill pill-success">POC Demo</span>
            <span className="pill">Local-first</span>
            <span className="pill">AI-Assisted</span>
          </div>
        </header>

        <ErrorBoundary key={activePage}>
          <div className="page-body">{children}</div>
        </ErrorBoundary>
      </main>
    </div>
  )
}
