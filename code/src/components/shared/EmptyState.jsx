export function EmptyState({ action, description, title }) {
  return (
    <div className="empty-state">
      <div className="empty-state-mark">AI</div>
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  )
}
