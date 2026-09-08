/**
 * The mark is a drawn glyph, not the letters "AI".
 *
 * It used to be a 76px chip containing the text "AI", which read as a brand
 * stamp on every empty panel — announcing the technology at the exact moment
 * the screen has nothing to show. An outlined tray says "nothing here yet",
 * which is what an empty state is for. It inherits `currentColor`, so the
 * existing `.empty-state-mark` colouring still applies.
 */
function EmptyMark() {
  return (
    <svg
      aria-hidden="true"
      fill="none"
      focusable="false"
      height="34"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="1.5"
      viewBox="0 0 24 24"
      width="34"
    >
      <path d="M3.5 13.5h4l1.4 2.4h6.2l1.4-2.4h4" />
      <path d="M5.4 5.6 3.5 13.5v4a1.6 1.6 0 0 0 1.6 1.6h13.8a1.6 1.6 0 0 0 1.6-1.6v-4L18.6 5.6a1.6 1.6 0 0 0-1.5-1.1H6.9a1.6 1.6 0 0 0-1.5 1.1Z" />
    </svg>
  )
}

export function EmptyState({ action, description, title }) {
  return (
    <div className="empty-state">
      <div className="empty-state-mark">
        <EmptyMark />
      </div>
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  )
}
