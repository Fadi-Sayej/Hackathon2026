// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { cleanup, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { renderWithI18n } from '../../../test/renderWithI18n.jsx'
import { ReceivingCaptureForm } from '../ReceivingCaptureForm.jsx'
import {
  EXPIRY_QUEUE_KEY,
  LAST_SUPPLIER_KEY,
  RECEIVING_QUEUE_KEY,
} from '../../../lib/receiving/receivingQueue.js'

const PRODUCTS = [{ id: 'ym-7290000066318', name: 'קוקה קולה 1.5 ליטר' }]

// Every caption in this form comes from the dictionaries, so it cannot render
// outside the provider. English is the chosen language purely so the queries
// below read as the labels a user sees; the behaviour under test is the same in
// all three.
const render = (ui) => renderWithI18n(ui, { language: 'en' })

afterEach(cleanup)
beforeEach(() => {
  globalThis.localStorage.clear()
})

function fields() {
  return {
    barcode: screen.getByLabelText(/barcode/i),
    quantity: screen.getByLabelText(/quantity/i),
    supplier: screen.getByLabelText(/supplier/i),
    unitCost: screen.getByLabelText(/unit cost/i),
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

  // A phone that pops a full QWERTY keyboard for a barcode or a quantity costs
  // seconds on every single line — against a 20-second-per-line budget, that is
  // the difference between the tool winning and losing to a pen. inputMode is
  // what tells the phone to show digits instead, so it is worth locking in as
  // an assertion and not just a one-time manual glance.
  it('requests a numeric keypad for barcode and quantity, and a decimal keypad for unit cost', () => {
    render(<ReceivingCaptureForm products={PRODUCTS} />)
    const el = fields()
    expect(el.barcode.getAttribute('inputmode')).toBe('numeric')
    expect(el.quantity.getAttribute('inputmode')).toBe('numeric')
    expect(el.unitCost.getAttribute('inputmode')).toBe('decimal')
  })

  it('offers previously used suppliers in the datalist after two lines from different suppliers', async () => {
    const user = userEvent.setup()
    const { container } = render(<ReceivingCaptureForm products={PRODUCTS} />)
    await recordOneLine(user, { barcode: '111', quantity: '5', supplier: 'Tempo' })
    await recordOneLine(user, { barcode: '222', quantity: '6', supplier: 'Osem' })

    const options = [...container.querySelectorAll('#receiving-suppliers option')].map(
      (option) => option.value,
    )
    expect(options).toContain('Tempo')
    expect(options).toContain('Osem')
  })

  // The bolded requirement is scan -> focus jumps -> Enter -> saved, without a
  // hand leaving the barcode gun. Every other test here clicks Save, which
  // proves the form works but not that the speed path does: the last hop, Enter
  // in the quantity field submitting, was asserted by nothing.
  it('saves a line with the keyboard alone — no click anywhere', async () => {
    const user = userEvent.setup()
    render(<ReceivingCaptureForm products={PRODUCTS} />)

    // Supplier is the one field a gun cannot fill; it is typed once and then
    // remembered, so the per-line path below never touches it again.
    await user.type(fields().supplier, 'Tempo')

    fields().barcode.focus()
    await user.keyboard('7290000066318{Enter}')      // the gun's own Enter
    expect(document.activeElement).toBe(fields().quantity)
    await user.keyboard('24{Enter}')                 // and the worker's

    expect(screen.getByText(/saved: 24 ×/i)).toBeDefined()
    expect(screen.getByRole('button', { name: /download 1 recorded line/i })).toBeDefined()
    expect(document.activeElement).toBe(fields().barcode)

    // And straight into the next line, still without touching the mouse.
    await user.keyboard('111{Enter}')
    await user.keyboard('6{Enter}')
    expect(screen.getByRole('button', { name: /download 2 recorded lines/i })).toBeDefined()
  })
})

describe('ReceivingCaptureForm — expiry-only mode', () => {
  function switchToExpiryOnly(user) {
    return user.click(screen.getByLabelText(/expiry only/i))
  }

  it('drops the quantity and supplier fields the delivery path requires', async () => {
    const user = userEvent.setup()
    render(<ReceivingCaptureForm products={PRODUCTS} />)
    expect(screen.getByLabelText(/quantity/i)).toBeDefined()

    await switchToExpiryOnly(user)
    expect(screen.queryByLabelText(/quantity/i)).toBeNull()
    expect(screen.queryByLabelText(/supplier/i)).toBeNull()
    expect(screen.queryByLabelText(/unit cost/i)).toBeNull()
    expect(screen.getByLabelText(/expiry date/i)).toBeDefined()
  })

  it('records a date for stock already on the shelf, with no supplier invented', async () => {
    const user = userEvent.setup()
    render(<ReceivingCaptureForm products={PRODUCTS} />)
    await switchToExpiryOnly(user)

    await user.type(screen.getByLabelText(/barcode/i), '7290000066318')
    await user.type(screen.getByLabelText(/expiry date/i), '2026-12-31')
    await user.click(screen.getByRole('button', { name: /^save$/i }))

    expect(screen.getByText(/saved:/i)).toBeDefined()
    const stored = JSON.parse(globalThis.localStorage.getItem(EXPIRY_QUEUE_KEY))
    expect(stored).toHaveLength(1)
    expect(stored[0]).toMatchObject({ barcode: '7290000066318', expiryDate: '2026-12-31' })
    expect(stored[0].supplier).toBeUndefined()
    expect(stored[0].quantity).toBeUndefined()
  })

  it('refuses a line with no expiry date, which is the whole point of the mode', async () => {
    const user = userEvent.setup()
    render(<ReceivingCaptureForm products={PRODUCTS} />)
    await switchToExpiryOnly(user)

    await user.type(screen.getByLabelText(/barcode/i), '7290000066318')
    await user.click(screen.getByRole('button', { name: /^save$/i }))
    expect(screen.getByText(/enter the expiry date printed on the package/i)).toBeDefined()
    expect(screen.queryByRole('button', { name: /download/i })).toBeNull()
  })

  it('keeps the two lists apart so an expiry line never lands in the ledger', async () => {
    const user = userEvent.setup()
    render(<ReceivingCaptureForm products={PRODUCTS} />)
    await recordOneLine(user, { barcode: '111', quantity: '5', supplier: 'Tempo' })

    await switchToExpiryOnly(user)
    // The delivery list is not showing here, and the expiry list is empty.
    expect(screen.queryByRole('button', { name: /download/i })).toBeNull()

    await user.type(screen.getByLabelText(/barcode/i), '222')
    await user.type(screen.getByLabelText(/expiry date/i), '2026-12-31')
    await user.click(screen.getByRole('button', { name: /^save$/i }))

    expect(JSON.parse(globalThis.localStorage.getItem(RECEIVING_QUEUE_KEY))).toHaveLength(1)
    expect(JSON.parse(globalThis.localStorage.getItem(EXPIRY_QUEUE_KEY))).toHaveLength(1)
  })

  it('fills the date from a quick-date button', async () => {
    const user = userEvent.setup()
    render(<ReceivingCaptureForm products={PRODUCTS} />)
    await switchToExpiryOnly(user)

    await user.click(screen.getByRole('button', { name: /1 week/i }))
    const expected = new Date()
    expected.setDate(expected.getDate() + 7)
    const pad = (n) => String(n).padStart(2, '0')
    expect(screen.getByLabelText(/expiry date/i).value).toBe(
      `${expected.getFullYear()}-${pad(expected.getMonth() + 1)}-${pad(expected.getDate())}`,
    )
  })
})
