// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { ReceivingCaptureForm } from '../ReceivingCaptureForm.jsx'
import { RECEIVING_QUEUE_KEY, LAST_SUPPLIER_KEY } from '../../../lib/receiving/receivingQueue.js'

const PRODUCTS = [{ id: 'ym-7290000066318', name: 'קוקה קולה 1.5 ליטר' }]

afterEach(cleanup)
beforeEach(() => {
  globalThis.localStorage.clear()
})

function fields() {
  return {
    barcode: screen.getByLabelText(/barcode/i),
    quantity: screen.getByLabelText(/quantity/i),
    supplier: screen.getByLabelText(/supplier/i),
    save: screen.getByRole('button', { name: /^save$/i }),
  }
}

async function recordOneLine(user, { barcode = '7290000066318', quantity = '24', supplier = 'Tempo' } = {}) {
  const el = fields()
  await user.clear(el.barcode)
  await user.type(el.barcode, barcode)
  await user.clear(el.quantity)
  await user.type(el.quantity, quantity)
  await user.clear(el.supplier)
  await user.type(el.supplier, supplier)
  await user.click(el.save)
}

describe('ReceivingCaptureForm', () => {
  it('shows the Hebrew product name as soon as a known barcode is entered', async () => {
    const user = userEvent.setup()
    render(<ReceivingCaptureForm products={PRODUCTS} />)
    await user.type(fields().barcode, '7290000066318')
    expect(screen.getByText(/קוקה קולה 1.5 ליטר/)).toBeDefined()
  })

  it('warns but still allows a barcode that is not in the catalog', async () => {
    const user = userEvent.setup()
    render(<ReceivingCaptureForm products={PRODUCTS} />)
    await user.type(fields().barcode, '999')
    expect(screen.getByText(/not found in the catalog/i)).toBeDefined()
  })

  it('moves focus to quantity on Enter in the barcode field instead of submitting', async () => {
    const user = userEvent.setup()
    render(<ReceivingCaptureForm products={PRODUCTS} />)
    const el = fields()
    await user.type(el.barcode, '7290000066318{Enter}')
    expect(document.activeElement).toBe(el.quantity)
    // Nothing was saved: no queue list appeared.
    expect(screen.queryByRole('button', { name: /download/i })).toBeNull()
  })

  it('saves a line and returns focus to the barcode field', async () => {
    const user = userEvent.setup()
    render(<ReceivingCaptureForm products={PRODUCTS} />)
    await recordOneLine(user)
    expect(screen.getByText(/saved:/i)).toBeDefined()
    expect(document.activeElement).toBe(fields().barcode)
  })

  it('keeps the supplier but clears barcode and quantity between lines', async () => {
    const user = userEvent.setup()
    render(<ReceivingCaptureForm products={PRODUCTS} />)
    await recordOneLine(user, { supplier: 'Tempo' })
    const el = fields()
    expect(el.supplier.value).toBe('Tempo')
    expect(el.barcode.value).toBe('')
    expect(el.quantity.value).toBe('')
  })

  it('shows the validation message and saves nothing when quantity is empty', async () => {
    const user = userEvent.setup()
    render(<ReceivingCaptureForm products={PRODUCTS} />)
    const el = fields()
    await user.type(el.barcode, '7290000066318')
    await user.type(el.supplier, 'Tempo')
    await user.click(el.save)
    expect(screen.getByText(/quantity must be a whole number/i)).toBeDefined()
    expect(screen.queryByRole('button', { name: /download/i })).toBeNull()
  })

  it('undo removes only the most recent line', async () => {
    const user = userEvent.setup()
    render(<ReceivingCaptureForm products={PRODUCTS} />)
    await recordOneLine(user, { barcode: '111', quantity: '5' })
    await recordOneLine(user, { barcode: '222', quantity: '6' })
    expect(screen.getByRole('button', { name: /download 2 recorded lines/i })).toBeDefined()

    await user.click(screen.getByRole('button', { name: /undo last/i }))
    expect(screen.getByRole('button', { name: /download 1 recorded line/i })).toBeDefined()
  })

  it('the queue survives a remount, and the supplier pre-fills', async () => {
    const user = userEvent.setup()
    const { unmount } = render(<ReceivingCaptureForm products={PRODUCTS} />)
    await recordOneLine(user, { supplier: 'Osem' })
    expect(globalThis.localStorage.getItem(RECEIVING_QUEUE_KEY)).toContain('Osem')
    expect(globalThis.localStorage.getItem(LAST_SUPPLIER_KEY)).toBe('Osem')

    unmount()
    render(<ReceivingCaptureForm products={PRODUCTS} />)
    expect(screen.getByRole('button', { name: /download 1 recorded line/i })).toBeDefined()
    expect(fields().supplier.value).toBe('Osem')
  })
})
