export function StatusBadge({ children, tone = 'neutral' }) {
  return <span className={`status-badge status-badge-${tone}`}>{children}</span>
}
