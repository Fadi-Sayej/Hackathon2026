import { createHash } from 'node:crypto'
import { describe, expect, it, vi } from 'vitest'

import { AS_TAKEN_MAX, PART_MAX, PHOTO_SCHEMA, asSent, sendPhoto, sentList, split } from '../shelfPhotos.js'

/**
 * D-37, ADR-042, F12-S1 FR-225: a photo sent as the nightly collects it. The Python side is
 * src/owner_state/shelf_photos.py, tested in tests/owner_state/test_shelf_photos.py.
 */
const jpeg = (size, fill = 7) => { const b = new Uint8Array(size).fill(fill); b.set([0xff, 0xd8, 0xff, 0xe0]); return b }
const file = (bytes, type = 'image/jpeg') => ({ type, size: bytes.length, arrayBuffer: async () => bytes.slice().buffer })

function recorder() {
  const writes = []
  return {
    writes,
    writePart: async (id, n, part) => { writes.push(['part', id, n, part]) },
    writeManifest: async (id, manifest) => { writes.push(['manifest', id, manifest]) },
  }
}

describe('sending a shelf photo (FR-225)', () => {
  it('sends a JPEG byte for byte, in parts, and the manifest last', async () => {
    const bytes = jpeg(2 * PART_MAX + 17)
    const r = recorder()
    await sendPhoto({ id: 'p1', unit: 'מקרר 1', file: file(bytes) }, { ...r, now: () => 1_000, online: () => true })
    expect(r.writes.map((w) => w[0])).toEqual(['part', 'part', 'part', 'manifest'])
    const joined = new Uint8Array(r.writes.slice(0, 3).flatMap((w) => [...w[3].data]))
    expect(joined).toEqual(bytes)
    expect(r.writes.slice(0, 3).map((w) => w[3].data.length)).toEqual([PART_MAX, PART_MAX, 17])
    expect(r.writes[3][2]).toEqual({
      schema: PHOTO_SCHEMA, unit: 'מקרר 1', sentAt: 1_000, size: bytes.length, parts: 3,
      sha256: createHash('sha256').update(bytes).digest('hex'), type: 'image/jpeg',
    })
  })

  it('writes nothing when the phone is offline', async () => {
    const r = recorder()
    await expect(sendPhoto({ id: 'p1', unit: 'u', file: file(jpeg(10)) }, { ...r, online: () => false })).rejects.toThrow('offline')
    expect(r.writes).toEqual([])
  })

  it('writes no manifest when a part fails, so nothing half sent is collected', async () => {
    const r = recorder()
    r.writePart = vi.fn().mockRejectedValueOnce(new Error('network'))
    await expect(sendPhoto({ id: 'p1', unit: 'u', file: file(jpeg(10)) }, { ...r, online: () => true })).rejects.toThrow('network')
    expect(r.writes).toEqual([])
  })

  it('says it did not send when the store\'s connection never answers', async () => {
    const r = recorder()
    r.writePart = () => new Promise(() => {})
    await expect(sendPhoto({ id: 'p1', unit: 'u', file: file(jpeg(10)) }, { ...r, online: () => true, timeoutMs: 5 }))
      .rejects.toThrow('timeout')
  })

  it('redraws only what is not a JPEG, or is larger than 12 MB', async () => {
    const redraw = vi.fn(async () => jpeg(5))
    expect(await asSent(file(jpeg(100)), redraw)).toEqual(jpeg(100))
    expect(redraw).not.toHaveBeenCalled()
    await asSent(file(new Uint8Array([0x89, 0x50, 0x4e, 0x47, 1, 2]), 'image/png'), redraw)
    await asSent(file(jpeg(AS_TAKEN_MAX + 1)), redraw)
    expect(redraw).toHaveBeenCalledTimes(2)
  })

  it('splits at the part size and never makes an empty part', () => {
    expect(split(jpeg(PART_MAX)).length).toBe(1)
    expect(split(jpeg(PART_MAX + 1)).map((p) => p.length)).toEqual([PART_MAX, 1])
  })
})

describe('the photos sent, with their state (FR-227)', () => {
  const collected = [
    { id: 'a', unit: 'מקרר 1', collected: '2026-10-10', read: '2026-10-11' },
    { id: 'b', unit: 'מדף יבש', collected: '2026-10-12', read: null },
  ]

  it('lists each photo once, at its latest state, the waiting ones first', () => {
    const list = sentList({
      collected,
      pending: [{ id: 'c', unit: 'מקרר 2', sentAt: 5 }, { id: 'b', unit: 'מדף יבש', sentAt: 1 }],
      mine: [{ id: 'd', unit: 'מקרר 3' }, { id: 'c', unit: 'מקרר 2' }],
    })
    expect(list).toEqual([
      { id: 'd', unit: 'מקרר 3', status: 'sent', date: null },
      { id: 'c', unit: 'מקרר 2', status: 'sent', date: null },
      { id: 'b', unit: 'מדף יבש', status: 'collected', date: '2026-10-12' },
      { id: 'a', unit: 'מקרר 1', status: 'read', date: '2026-10-11' },
    ])
  })

  it('is empty when nothing was sent', () => {
    expect(sentList({})).toEqual([])
  })
})
