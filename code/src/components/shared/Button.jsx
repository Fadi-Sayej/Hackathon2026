export function Button({ children, className = '', tone = 'secondary', ...props }) {
  return (
    <button className={`btn btn-${tone} ${className}`} type="button" {...props}>
      {children}
    </button>
  )
}
