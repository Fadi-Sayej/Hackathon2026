import { describe, expect, it } from 'vitest'
import { loadOrderExample } from '../loadOrderExample.js'

/** D-29: the preview shows only a file that says it is an example, and says so when it cannot. */
const respond = (body, ok = true) => async () => ({ ok, json: async () => body })

describe('loadOrderExample', () => {
  it('reads the example from /examples/, never from the store\'s own /data/', async () => {
    let asked
    await loadOrderExample({ fetchImpl: async (url) => { asked = url; return { ok: false } } })
    expect(asked).toBe('/examples/order-example.json')
  })

  it('returns a file that says it is an example', async () => {
    const example = { _example: 'A test shop', artefact: { capabilities: {} } }
    expect(await loadOrderExample({ fetchImpl: respond(example) })).toEqual({ status: 'ok', example })
  })

  it('refuses a file that does not say it is an example, such as the store\'s own artefact', async () => {
    expect(await loadOrderExample({ fetchImpl: respond({ artefact: { capabilities: {} } }) })).toEqual({ status: 'error' })
  })

  it('says it could not load it, rather than throwing', async () => {
    expect(await loadOrderExample({ fetchImpl: async () => { throw new Error('offline') } })).toEqual({ status: 'error' })
    expect(await loadOrderExample({ fetchImpl: respond({}, false) })).toEqual({ status: 'error' })
  })
})
