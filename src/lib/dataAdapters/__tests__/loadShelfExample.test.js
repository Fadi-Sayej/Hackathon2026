import { describe, expect, it } from 'vitest'
import { loadShelfExample } from '../loadShelfExample.js'

/** D-31: Shelf plan's preview shows only a file that says it is an example, and says so when it cannot. */
const respond = (body, ok = true) => async () => ({ ok, json: async () => body })

describe('loadShelfExample', () => {
  it('reads the example from /examples/, never from the store\'s own /data/', async () => {
    let asked
    await loadShelfExample({ fetchImpl: async (url) => { asked = url; return { ok: false } } })
    expect(asked).toBe('/examples/shelf-plan-example.json')
  })

  it('returns a file that says it is an example', async () => {
    const example = { _example: 'A test shop', artefact: { capabilities: {} } }
    expect(await loadShelfExample({ fetchImpl: respond(example) })).toEqual({ status: 'ok', example })
  })

  it('refuses a file that does not say it is an example, such as the store\'s own artefact', async () => {
    expect(await loadShelfExample({ fetchImpl: respond({ artefact: { capabilities: {} } }) })).toEqual({ status: 'error' })
  })

  it('says it could not load it, rather than throwing', async () => {
    expect(await loadShelfExample({ fetchImpl: async () => { throw new Error('offline') } })).toEqual({ status: 'error' })
    expect(await loadShelfExample({ fetchImpl: respond({}, false) })).toEqual({ status: 'error' })
  })
})
