/**
 * Where a signed-in account goes (ADR-029 §3), and which `next` values the gate may send us
 * back to. Only our own two pages: a `next` is never a URL, a protocol or a data file.
 */
export const TEAM_HOME = '/telemetry.html'

const PAGES = new Set(['/', TEAM_HOME])

export function safeNext(value) {
  return typeof value === 'string' && PAGES.has(value) ? value : null
}

export function landingFor(role, next) {
  const target = safeNext(next)
  // The gate refuses the owner the team's page; sending him there would only bounce.
  if (target === TEAM_HOME && role !== 'team') return '/'
  if (target) return target
  return role === 'team' ? TEAM_HOME : '/'
}
