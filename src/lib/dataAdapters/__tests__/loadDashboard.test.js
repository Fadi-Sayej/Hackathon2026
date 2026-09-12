import { describe, expect, it } from 'vitest'
import fixture from '../../../__fixtures__/dashboard.fixture.json'
import { loadDashboard } from '../loadDashboard'

const ok = (body) => async () => ({ ok: true, status: 200, json: async () => body })

describe('loadDashboard', () => {
  it('returns the artefact when its preconditions hold', async () => {
    const r = await loadDashboard({ fetchImpl: ok(fixture) })
    expect(r.status).toBe('ok')
    expect(r.artefact.schema_version).toBe(2)
    expect(r.reason).toBeNull()
  })

  it('reports an unreachable artefact without throwing', async () => {
    const r = await loadDashboard({ fetchImpl: async () => { throw new Error('offline') } })
    expect(r.status).toBe('unreachable')
    expect(r.artefact).toBeNull()
  })

  it('reports a 404 as unreachable, not as an empty dashboard', async () => {
    const r = await loadDashboard({ fetchImpl: async () => ({ ok: false, status: 404 }) })
    expect(r.status).toBe('unreachable')
    expect(r.artefact).toBeNull()
  })

  it('reports unparseable JSON as unreachable', async () => {
    const r = await loadDashboard({
      fetchImpl: async () => ({ ok: true, status: 200, json: async () => { throw new SyntaxError('bad') } }),
    })
    expect(r.status).toBe('unreachable')
  })

  it('refuses a schema version it cannot render', async () => {
    const r = await loadDashboard({ fetchImpl: ok({ ...fixture, schema_version: 1 }) })
    expect(r.status).toBe('invalid')
    expect(r.artefact).toBeNull()
    expect(r.reason).toMatch(/schema_version/)
  })

  it('refuses an artefact with no capabilities object', async () => {
    const r = await loadDashboard({ fetchImpl: ok({ ...fixture, capabilities: null }) })
    expect(r.status).toBe('invalid')
    expect(r.reason).toMatch(/capabilities/)
  })

  it('refuses a capability with no status rather than rendering it as empty', async () => {
    // AC-107: an unavailable capability must read as unavailable, never as zero findings.
    // Without the field that is not merely wrong, it is unachievable.
    const broken = structuredClone(fixture)
    const first = Object.keys(broken.capabilities)[0]
    delete broken.capabilities[first].status
    const r = await loadDashboard({ fetchImpl: ok(broken) })
    expect(r.status).toBe('invalid')
    expect(r.reason).toMatch(new RegExp(first))
  })

  it('never falls back to older data', async () => {
    // The one behaviour that matters more than the checks: an invalid artefact must not
    // cause yesterday's numbers to be shown as though they were today's.
    const r = await loadDashboard({ fetchImpl: ok({ ...fixture, schema_version: 99 }) })
    expect(r.artefact).toBeNull()
  })

  it('accepts the fixture’s unavailable capability as valid', async () => {
    const unavailable = Object.values(fixture.capabilities).filter((c) => c.status === 'unavailable')
    expect(unavailable.length).toBeGreaterThan(0)
    const r = await loadDashboard({ fetchImpl: ok(fixture) })
    expect(r.status).toBe('ok')
  })
})
