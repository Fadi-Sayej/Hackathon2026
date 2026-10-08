// @vitest-environment jsdom

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, screen, waitFor } from '@testing-library/react'

import { renderWithI18n } from '../../test/renderWithI18n.jsx'
import { ShelfPlanPage } from '../ShelfPlanPage.jsx'
import { StoreLayoutPage } from '../StoreLayoutPage.jsx'

/**
 * Phase 8 Task 8.9: Store layout and Shelf plan, as the repository owner approved them on
 * 2026-10-05 (docs/reviews/F12-screens-mockups.md). The filled states read the marked example,
 * which the engine builds (scripts/build_shelf_example.py), so every figure here is the engine's.
 */
afterEach(cleanup)

const EXAMPLE = JSON.parse(readFileSync(resolve(process.cwd(), 'public/examples/shelf-plan-example.json'), 'utf8'))
const clone = (x) => JSON.parse(JSON.stringify(x))
const unavailable = (id, reason) => ({ id, status: 'unavailable', unavailable_reason: reason, entries: [], counts: {}, thresholds: {} })
const F12 = ['layout_facts', 'shelf_plan', 'shelf_measurement', 'shelf_explanation']

function waiting(reason) {
  return { capabilities: Object.fromEntries(F12.map((id) => [id, unavailable(id, reason)])) }
}

function filled(edit = () => {}) {
  const art = clone(EXAMPLE.artefact)
  edit(art.capabilities)
  return art
}

const plan = (art) => [...art.capabilities.shelf_plan.entries].sort((a, b) => a.ordering_key.value - b.ordering_key.value)

describe('Store layout (F12-S1 FR-190, FR-191, FR-196)', () => {
  it('AC-172: with no layout file, it says the measurements have not been recorded', () => {
    renderWithI18n(<StoreLayoutPage artefact={waiting('no_store_layout')} catalogue={null} />, { language: 'en' })
    expect(screen.getByRole('heading', { name: 'The shelf measurements have not been recorded yet.' })).toBeTruthy()
    expect(document.querySelector('[data-capability="layout_facts"]')).not.toBeNull()
    expect(document.querySelector('.layout__fixture')).toBeNull()
  })

  it('names what was rejected when every unit in the file was', () => {
    const art = waiting('layout_all_rejected')
    art.capabilities.layout_facts.rejected = [{ kind: 'fixture', key: 'מקרר', reason: 'shelves must list at least one shelf' }]
    renderWithI18n(<StoreLayoutPage artefact={art} catalogue={null} />, { language: 'en' })
    expect(screen.getByText(/The reasons are below\./)).toBeTruthy()
    const item = document.querySelector('[data-missing="rejected"] li')
    expect(item.textContent).toContain('Shelf unit: מקרר')
    expect(item.textContent).toContain('shelves must list at least one shelf')
  })

  it('AC-173: shows every recorded unit, with its dates, eye level, rules and what is missing', () => {
    const art = filled()
    renderWithI18n(<StoreLayoutPage artefact={art} catalogue={EXAMPLE.catalogue} />, { language: 'en' })
    const facts = art.capabilities.layout_facts
    const cards = [...document.querySelectorAll('.layout__fixture')]
    expect(cards.map((c) => c.dataset.fixture)).toEqual(facts.fixture_order)
    const fridge = document.querySelector('[data-fixture="מקרר"]')
    expect(fridge.textContent).toContain('Chilled')
    expect(fridge.textContent).toContain('measured 1 Aug')
    expect(fridge.querySelector('[data-eye-level]').textContent).toContain('Shelf 2')
    expect(fridge.querySelector('[data-missing="width"]').textContent).toContain('סודה')   // a name, not a barcode
    expect(document.querySelector('[data-fixture="מדף יבש"] .layout__rules').textContent).toContain('At most 2 facings of במבה')
    expect(document.querySelector('[data-missing="rejected"]').textContent).toContain('Product width: 7299999')
  })

  it('lists the units in the order the file gives, even when their names read as numbers', () => {
    const art = filled((c) => {
      const f = c.layout_facts
      const [a, b] = f.fixture_order
      f.fixtures = { 1: f.fixtures[a], 2: f.fixtures[b] }
      f.fixture_order = ['2', '1']
      f.without_width = { 1: [], 2: [] }
      f.without_picture = { 1: [], 2: [] }
    })
    renderWithI18n(<StoreLayoutPage artefact={art} catalogue={null} />, { language: 'en' })
    expect([...document.querySelectorAll('.layout__fixture')].map((c) => c.dataset.fixture)).toEqual(['2', '1'])
  })
})

describe('Shelf plan, waiting (F12-S1 FR-194, FR-200)', () => {
  it('AC-172 and AC-189: the reason in his words, no plan, and the marked example offered', async () => {
    const load = vi.fn(async () => ({ status: 'ok', example: EXAMPLE }))
    const onOutcome = vi.fn()
    renderWithI18n(<ShelfPlanPage artefact={waiting('no_store_layout')} ownerState={{ outcomes: {} }} catalogue={null}
      onOutcome={onOutcome} loadExample={load} />, { language: 'en' })
    expect(screen.getByRole('heading', { name: 'The shelf measurements have not been recorded yet.' })).toBeTruthy()
    expect(document.querySelector('.plan__fixture')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'See how this page looks' }))
    await waitFor(() => expect(document.querySelector('.example .plan__fixture')).not.toBeNull())
    const arranged = [...document.querySelectorAll('.example [data-action="arranged"]')]
    expect(arranged.length).toBe(3)
    for (const button of arranged) {
      expect(button.disabled).toBe(true)
      fireEvent.click(button)
    }
    expect(onOutcome).not.toHaveBeenCalled()
  })

  it('AC-173: waits for the daily reports with the plan\'s own sentence', () => {
    renderWithI18n(<ShelfPlanPage artefact={waiting('no_daily_sales')} ownerState={{ outcomes: {} }} catalogue={null} />,
      { language: 'en' })
    expect(screen.getByRole('heading', { name: 'We are waiting for the daily sales reports: a shelf plan needs sales per day.' })).toBeTruthy()
    expect(document.querySelector('.plan__fixture')).toBeNull()
  })
})

describe('Shelf plan, filled (F12-S1 FR-194, FR-201, FR-215, FR-217)', () => {
  it('draws each unit from the front: one tile per facing, numbered for the key', () => {
    const art = filled()
    renderWithI18n(<ShelfPlanPage artefact={art} ownerState={{ outcomes: {} }} catalogue={EXAMPLE.catalogue} />, { language: 'en' })
    for (const entry of plan(art)) {
      const card = document.querySelector(`[data-fixture="${entry.evidence.fixture}"]`)
      const facings = entry.evidence.shelves.flatMap((s) => s.products).reduce((n, p) => n + p.facings, 0)
      expect(card.querySelectorAll('.unit__tile').length).toBe(facings)
      const names = entry.evidence.shelves.flatMap((s) => s.products.map((p) => p.product_name))
      expect([...card.querySelectorAll('.unit__key .plan__product-name')].map((n) => n.textContent)).toEqual(names)
    }
    const fridge = document.querySelector('[data-fixture="מקרר"]')
    expect(fridge.querySelector('[data-unplaced="no_width"]').textContent).toContain('סודה')
    expect(fridge.textContent).toContain('No extra facings on this unit')
    expect(document.querySelector('.plan__conditions').textContent).toContain('0.17')
  })

  it('shows a product\'s own picture on its tiles, and a numbered tile without one', () => {
    const art = filled((c) => { c.shelf_plan.entries.forEach((e) => e.evidence.shelves?.forEach((s) => s.products.forEach((p, i) => {
      if (i === 0) p.picture = `/store/shelf-pictures/${p.barcode}.png?v=2026-08-01`
    }))) })
    renderWithI18n(<ShelfPlanPage artefact={art} ownerState={{ outcomes: {} }} catalogue={EXAMPLE.catalogue} />, { language: 'en' })
    const pictured = [...document.querySelectorAll('.unit__tile[data-picture] img')]
    expect(pictured.length).toBeGreaterThan(0)
    expect(pictured[0].getAttribute('src')).toMatch(/^\/store\/shelf-pictures\/\d+\.png\?v=2026-08-01$/)
    expect(document.querySelectorAll('.unit__tile:not([data-picture])').length).toBeGreaterThan(0)
    expect(screen.getAllByText(/A numbered tile means that product's picture has not been taken yet\./).length).toBeGreaterThan(0)
  })

  it('AC-204: the AI\'s explanation in the page\'s language, or the reason it has none', () => {
    const art = filled((c) => {
      const [first, second] = c.shelf_explanation.explanations
      Object.assign(first, { text: { en: 'English words', he: 'מילים בעברית', ar: 'كلمات' }, why_none: null })
      Object.assign(second, { why_none: 'withheld' })
    })
    renderWithI18n(<ShelfPlanPage artefact={art} ownerState={{ outcomes: {} }} catalogue={EXAMPLE.catalogue} />, { language: 'he' })
    const panels = [...document.querySelectorAll('.plan__why')].map((p) => p.dataset.explanation)
    expect(panels).toContain('shown')
    expect(panels).toContain('withheld')
    expect(screen.getByText('מילים בעברית')).toBeTruthy()
    cleanup()
    const off = filled((c) => { c.shelf_explanation = unavailable('shelf_explanation', 'no_model_key') })
    renderWithI18n(<ShelfPlanPage artefact={off} ownerState={{ outcomes: {} }} catalogue={EXAMPLE.catalogue} />, { language: 'en' })
    expect(screen.getAllByText('The shelf explanation is off: no key for the model has been set up.').length).toBe(3)
  })

  it('AC-190: pressing "I\'ve arranged this shelf" records the acted outcome; the device then shows it, with undo', () => {
    const art = filled()
    const entry = plan(art)[0]
    const onOutcome = vi.fn()
    const onUndo = vi.fn()
    renderWithI18n(<ShelfPlanPage artefact={art} ownerState={{ outcomes: {} }} catalogue={EXAMPLE.catalogue}
      onOutcome={onOutcome} onUndoOutcome={onUndo} />, { language: 'en' })
    const card = document.querySelector(`[data-fixture="${entry.evidence.fixture}"]`)
    fireEvent.click(card.querySelector('[data-action="arranged"]'))
    expect(onOutcome).toHaveBeenCalledTimes(1)
    expect(onOutcome).toHaveBeenCalledWith(entry, { status: 'acted' })
    cleanup()
    const outcomes = { [entry.id]: { status: 'acted', snapshot: { arranged_on: '2026-08-28' } } }
    renderWithI18n(<ShelfPlanPage artefact={art} ownerState={{ outcomes }} catalogue={EXAMPLE.catalogue}
      onOutcome={onOutcome} onUndoOutcome={onUndo} />, { language: 'en' })
    const mine = document.querySelector(`[data-fixture="${entry.evidence.fixture}"] [data-arranged="this-device"]`)
    expect(mine.textContent).toContain('You marked it arranged on 28 Aug.')
    fireEvent.click(mine.querySelector('[data-action="undo"]'))
    expect(onUndo).toHaveBeenCalledWith(entry.id)
  })

  it('AC-182: a team account sees the button disabled, and its press writes nothing', () => {
    const onOutcome = vi.fn()
    renderWithI18n(<ShelfPlanPage artefact={filled()} ownerState={{ outcomes: {} }} catalogue={EXAMPLE.catalogue}
      onOutcome={onOutcome} readOnly />, { language: 'en' })
    for (const button of document.querySelectorAll('[data-action="arranged"]')) {
      expect(button.disabled).toBe(true)
      fireEvent.click(button)
    }
    expect(onOutcome).not.toHaveBeenCalled()
  })

  it('shows the published arrangement, warns while its measurement runs, and states his store\'s figure', () => {
    const art = filled((c) => {
      const fixture = c.shelf_plan.entries[0].evidence.fixture
      c.shelf_measurement = {
        id: 'shelf_measurement', status: 'available', unavailable_reason: null, entries: [], counts: {},
        thresholds: { min_arrangements: 8, min_products: 40 },
        arrangements: [{
          entry_id: 'abc', fixture, arranged_on: '2026-08-20', plan_date: '2026-08-18',
          before_window: { first_day: '2026-06-23', last_day: '2026-07-20' },
          after_window: { first_day: '2026-08-21', last_day: '2026-09-17' },
          status: 'waiting', reason: null, waiting: { report_days_so_far: 6, report_days_needed: 21, days_left: 22 },
          comparison: null, products: [], left_out: [],
        }],
        elasticity: { estimate: 0.186, interval: [0.167, 0.203], level: 0.95, verdict: 'measured', why_not_measurable: null,
          arrangements: 8, fixtures: 8, products: 48 },
        placebo: { status: 'passed', failed_on: [] },
      }
    })
    renderWithI18n(<ShelfPlanPage artefact={art} ownerState={{ outcomes: {} }} catalogue={EXAMPLE.catalogue} />, { language: 'en' })
    expect(screen.getByText('Arranged on 20 Aug, to the plan of 18 Aug.', { exact: false })).toBeTruthy()
    expect(screen.getByText(/Being measured: 6 report days so far, of the 21 needed\. The after window ends in 22 days\./)).toBeTruthy()
    expect(screen.getByRole('note').textContent).toContain('Arranging it again ends that measurement.')
    const figure = document.querySelector('.plan__store')
    expect(figure.textContent).toContain('Your store: 0.19, most likely between 0.17 and 0.20 (95% interval).')
    expect(figure.textContent).toContain('Check for earlier trends: passed.')
  })
})

describe('The shelf reader\'s widths, waiting for their acceptance run (F12-S1 FR-223)', () => {
  const reader = (status) => ({ status, read_on: '2026-10-10', widths: 42,
    acceptance: { listed: 7, within: 6, minimum: 20, tolerance_mm: 5 } })
  const SENTENCE = 'The shelf reader read 42 widths from your photos on 10 Oct. They are used once its check passes: '
    + '20 products measured by hand, each within 5 mm of the reader\'s width. So far: 6 of 7.'

  it('says so at the top of Store layout and under the plan\'s conditions on Shelf plan', () => {
    const art = filled((c) => { c.layout_facts.reader = reader('waiting_for_acceptance') })
    renderWithI18n(<StoreLayoutPage artefact={art} catalogue={EXAMPLE.catalogue} />, { language: 'en' })
    expect(document.querySelector('[data-reader="waiting_for_acceptance"]').textContent).toBe(SENTENCE)
    cleanup()
    renderWithI18n(<ShelfPlanPage artefact={art} ownerState={{ outcomes: {} }} catalogue={EXAMPLE.catalogue} />, { language: 'en' })
    const sentence = document.querySelector('[data-reader="waiting_for_acceptance"]')
    expect(sentence.textContent).toBe(SENTENCE)
    expect(sentence.previousElementSibling.dataset.elasticity).toBeTruthy()
  })

  it('says nothing once the run has passed, or before anything was read', () => {
    for (const status of ['accepted', 'no_readings']) {
      const art = filled((c) => { c.layout_facts.reader = reader(status) })
      renderWithI18n(<StoreLayoutPage artefact={art} catalogue={EXAMPLE.catalogue} />, { language: 'en' })
      expect(document.querySelector('[data-reader]')).toBeNull()
      cleanup()
    }
  })

  it('reads in Hebrew and Arabic, with no key left showing', () => {
    const art = filled((c) => { c.layout_facts.reader = reader('waiting_for_acceptance') })
    for (const language of ['he', 'ar']) {
      renderWithI18n(<StoreLayoutPage artefact={art} catalogue={EXAMPLE.catalogue} />, { language })
      const text = document.querySelector('[data-reader]').textContent
      expect(text).not.toMatch(/layout\.reader|\{/)
      expect(text).toContain('42')
      cleanup()
    }
  })
})

describe('Sending the shelf photos (F12-S1 FR-224, FR-227; D-37, ADR-042)', () => {
  const photo = () => new File([new Uint8Array([0xff, 0xd8, 0xff, 0xe0])], 'unit.jpg', { type: 'image/jpeg' })
  const choose = () => fireEvent.change(document.querySelector('.photos input[type=file]'), { target: { files: [photo()] } })
  const send = () => document.querySelector('[data-action="send-photo"]')
  globalThis.URL.createObjectURL ??= () => 'blob:preview'
  globalThis.URL.revokeObjectURL ??= () => {}

  it('is not shown where nothing could be sent', () => {
    renderWithI18n(<StoreLayoutPage artefact={waiting('no_store_layout')} catalogue={null} />, { language: 'en' })
    expect(document.querySelector('.photos')).toBeNull()
  })

  it('with no layout yet, the unit is typed, and Send waits for a name and a photo', async () => {
    const onSend = vi.fn(async () => {})
    renderWithI18n(<StoreLayoutPage artefact={waiting('no_store_layout')} catalogue={null} photos={{ onSend }} />, { language: 'en' })
    expect(screen.getByRole('heading', { name: 'Send photos of your shelves' })).toBeTruthy()
    expect(send().disabled).toBe(true)
    choose()
    expect(send().disabled).toBe(true)
    fireEvent.change(screen.getByPlaceholderText('The unit\'s name, such as “Fridge 1”'), { target: { value: ' Fridge 1 ' } })
    expect(send().disabled).toBe(false)
    fireEvent.click(send())
    await screen.findByText('Sent. It reaches the shelf reader tonight.')
    const [unit, file, id] = onSend.mock.calls[0]
    expect([unit, file.name, typeof id]).toEqual(['Fridge 1', 'unit.jpg', 'string'])
    expect(document.querySelector('.photos__sent').textContent).toContain('Fridge 1 · sent, collected tonight')
  })

  it('sending the same photo again sends it under the same id', async () => {
    const onSend = vi.fn().mockRejectedValueOnce(new Error('network')).mockResolvedValueOnce()
    renderWithI18n(<StoreLayoutPage artefact={waiting('no_store_layout')} catalogue={null} photos={{ onSend }} />, { language: 'en' })
    fireEvent.change(document.querySelector('.photos input[type=text]'), { target: { value: 'Fridge 1' } })
    choose()
    fireEvent.click(send())
    await screen.findByText('It did not send. Check the connection and try again.')
    fireEvent.click(send())
    await screen.findByText('Sent. It reaches the shelf reader tonight.')
    expect(onSend.mock.calls[1][2]).toBe(onSend.mock.calls[0][2])
  })

  it('with units recorded, the unit is chosen from them, or typed as another', () => {
    const art = filled()
    renderWithI18n(<StoreLayoutPage artefact={art} catalogue={null} photos={{ onSend: vi.fn() }} />, { language: 'en' })
    const options = [...document.querySelectorAll('.photos select option')].map((o) => o.textContent)
    expect(options).toEqual([...art.capabilities.layout_facts.fixture_order, 'Another unit'])
    expect(document.querySelector('.photos input[type=text]')).toBeNull()
    fireEvent.change(document.querySelector('.photos select'), { target: { value: '__other' } })
    expect(document.querySelector('.photos input[type=text]')).not.toBeNull()
  })

  it('lists what is waiting, collected and read', async () => {
    const art = waiting('no_store_layout')
    art.capabilities.layout_facts.photos = [
      { id: 'a', unit: 'מקרר 1', collected: '2026-10-10', read: '2026-10-11' },
      { id: 'b', unit: 'מדף יבש', collected: '2026-10-12', read: null },
    ]
    const loadPending = async () => [{ id: 'c', unit: 'מקרר 2', sentAt: 1 }]
    renderWithI18n(<StoreLayoutPage artefact={art} catalogue={null} photos={{ onSend: vi.fn(), loadPending }} />, { language: 'en' })
    await waitFor(() => expect(document.querySelectorAll('.photos__sent li').length).toBe(3))
    expect([...document.querySelectorAll('.photos__sent li')].map((li) => li.textContent)).toEqual([
      'מקרר 2 · sent, collected tonight', 'מדף יבש · collected 12 Oct', 'מקרר 1 · read 11 Oct',
    ])
  })

  it('a team account sees it disabled, and can send nothing', () => {
    const onSend = vi.fn()
    renderWithI18n(<StoreLayoutPage artefact={filled()} catalogue={null} photos={{ onSend, readOnly: true }} />, { language: 'en' })
    expect(document.querySelector('.photos select').disabled).toBe(true)
    expect(document.querySelector('.photos input[type=file]').disabled).toBe(true)
    expect(send().disabled).toBe(true)
    expect(document.querySelector('.photos__choose').dataset.disabled).toBe('true')
  })
})

describe('The owner\'s own units (F12-S1 FR-228; D-38, ADR-044)', () => {
  const catalogue = { products: [{ barcode: '1', department: 'drinks', product_name: 'מים' }, { barcode: '2', department: 'snacks', product_name: 'במבה' }] }
  const form = () => document.querySelector('.units')

  it('is not shown where nothing could be saved', () => {
    renderWithI18n(<StoreLayoutPage artefact={waiting('no_store_layout')} catalogue={catalogue} />, { language: 'en' })
    expect(form()).toBeNull()
  })

  it('adds a unit and saves the whole list, once it has a name, a department and its sizes', async () => {
    const onSave = vi.fn(async () => {})
    renderWithI18n(<StoreLayoutPage artefact={waiting('no_store_layout')} catalogue={catalogue} units={{ onSave }} />, { language: 'en' })
    expect(screen.getByText('No unit is described yet.')).toBeTruthy()
    fireEvent.click(document.querySelector('[data-action="add-unit"]'))
    const save = () => document.querySelector('[data-action="save-unit"]')
    expect(save().disabled).toBe(true)
    fireEvent.change(document.querySelector('.units__editor input[type=text]'), { target: { value: 'Fridge 1' } })
    fireEvent.change(document.querySelector('.units__editor select'), { target: { value: 'drinks' } })
    const [length] = document.querySelectorAll('.units__shelf[data-shelf="1"] input')
    fireEvent.change(length, { target: { value: '100' } })
    expect(save().disabled).toBe(false)
    fireEvent.click(save())
    await screen.findByText('Saved. The plan uses it from tonight.')
    expect(onSave).toHaveBeenCalledWith([{ name: 'Fridge 1', departments: ['drinks'], chilled: false, eye_level_shelf: null,
      shelves: [{ length_cm: 100, height_cm: null }] }])
    expect(form().textContent).toContain('100 cm, open above')
  })

  it('starts from the published units, and from a newer save the file has not taken', async () => {
    const art = filled()
    const loadSaved = async () => ({ schema: 1, saved_at: '2099-01-01T00:00:00.000Z',
      units: [{ name: 'Saved unit', departments: ['drinks'], chilled: false, eye_level_shelf: null, shelves: [{ length_cm: 50, height_cm: 30 }] }] })
    renderWithI18n(<StoreLayoutPage artefact={art} catalogue={catalogue} units={{ onSave: vi.fn() }} />, { language: 'en' })
    expect([...document.querySelectorAll('.units__item')].map((li) => li.dataset.unit)).toEqual(art.capabilities.layout_facts.fixture_order)
    cleanup()
    renderWithI18n(<StoreLayoutPage artefact={art} catalogue={catalogue} units={{ onSave: vi.fn(), loadSaved }} />, { language: 'en' })
    await waitFor(() => expect([...document.querySelectorAll('.units__item')].map((li) => li.dataset.unit)).toEqual(['Saved unit']))
  })

  it('says when it did not save, and keeps the unit open', async () => {
    const onSave = vi.fn().mockRejectedValue(new Error('network'))
    renderWithI18n(<StoreLayoutPage artefact={filled()} catalogue={catalogue} units={{ onSave }} />, { language: 'en' })
    fireEvent.click(document.querySelector('.units__item button'))
    // A unit recorded before D-38 has no heights: Save waits for each shelf's below the top.
    expect(document.querySelector('[data-action="save-unit"]').disabled).toBe(true)
    for (const row of [...document.querySelectorAll('.units__shelf')].slice(1)) {
      fireEvent.change(row.querySelectorAll('input')[1], { target: { value: '35' } })
    }
    fireEvent.click(document.querySelector('[data-action="save-unit"]'))
    await screen.findByText('It did not save. Check the connection and try again.')
    expect(document.querySelector('.units__editor')).not.toBeNull()
  })

  it('a team account sees it disabled', () => {
    renderWithI18n(<StoreLayoutPage artefact={filled()} catalogue={catalogue} units={{ onSave: vi.fn(), readOnly: true }} />, { language: 'en' })
    expect(document.querySelector('[data-action="add-unit"]').disabled).toBe(true)
    expect([...document.querySelectorAll('.units__item button')].every((b) => b.disabled)).toBe(true)
  })
})
