import { describe, expect, it } from 'vitest'

import { loadMeasurement } from '../loadMeasurement.js'

/**
 * F13-S1. Until the nightly first writes public/data/measurement.json there is no file, and
 * vercel.json rewrites every unmatched path to index.html: a missing file answers 200 with the
 * app's HTML, not 404. Either way it is "not published yet", never a parse error.
 */
const response = ({ status = 200, type = 'application/json', body = '{}' } = {}) => ({
  ok: status >= 200 && status < 300,
  status,
  headers: { get: (name) => (name.toLowerCase() === 'content-type' ? type : null) },
  json: async () => JSON.parse(body),
})

describe('loadMeasurement', () => {
  it('returns the file', async () => {
    const result = await loadMeasurement(async () => response({ body: '{"status":"available"}' }))
    expect(result).toEqual({ status: 'ok', body: { status: 'available' } })
  })

  it('reads the SPA fallback as not published yet', async () => {
    const result = await loadMeasurement(async () => response({ type: 'text/html; charset=utf-8', body: '<!doctype html>' }))
    expect(result).toEqual({ status: 'missing' })
  })

  it('reads a 404 as not published yet', async () => {
    expect(await loadMeasurement(async () => response({ status: 404 }))).toEqual({ status: 'missing' })
  })

  it('reads a refusal as unreachable, with its status', async () => {
    expect(await loadMeasurement(async () => response({ status: 403 }))).toEqual({ status: 'unreachable', reason: 'HTTP 403' })
  })
})
