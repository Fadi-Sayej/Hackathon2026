// @vitest-environment jsdom

import { afterEach, describe, expect, it } from 'vitest'
import { shouldPreventSmoothScroll } from '../preventSmoothScroll.js'

/**
 * Lenis takes the wheel for the whole document, which also takes it from every
 * scrollable element inside it. The sidebar stopped scrolling the day smooth
 * scrolling arrived, and nothing about the symptom points at the cause.
 */

function element({ overflowY = 'visible', overflowX = 'visible', scrollHeight = 100, clientHeight = 100,
                   scrollWidth = 100, clientWidth = 100, attr = false } = {}) {
  const node = document.createElement('div')
  node.style.overflowY = overflowY
  node.style.overflowX = overflowX
  if (attr) node.setAttribute('data-lenis-prevent', '')
  Object.defineProperties(node, {
    scrollHeight: { value: scrollHeight, configurable: true },
    clientHeight: { value: clientHeight, configurable: true },
    scrollWidth: { value: scrollWidth, configurable: true },
    clientWidth: { value: clientWidth, configurable: true },
  })
  document.body.appendChild(node)
  return node
}

afterEach(() => { document.body.innerHTML = '' })

describe('shouldPreventSmoothScroll', () => {
  it('yields to a vertical scroller with more content than room — the sidebar', () => {
    expect(shouldPreventSmoothScroll(element({ overflowY: 'auto', scrollHeight: 900, clientHeight: 400 }))).toBe(true)
  })

  it('yields to a horizontal scroller — the wide tables', () => {
    expect(shouldPreventSmoothScroll(element({ overflowX: 'auto', scrollWidth: 1600, clientWidth: 700 }))).toBe(true)
  })

  it('does not yield when there is nothing to scroll', () => {
    // overflow:auto on an element that fits must not steal the wheel from the page.
    expect(shouldPreventSmoothScroll(element({ overflowY: 'auto', scrollHeight: 100, clientHeight: 100 }))).toBe(false)
  })

  it('does not yield for an ordinary element', () => {
    expect(shouldPreventSmoothScroll(element())).toBe(false)
  })

  it('honours an explicit data-lenis-prevent even with nothing to scroll', () => {
    expect(shouldPreventSmoothScroll(element({ attr: true }))).toBe(true)
  })

  it('survives a non-element node', () => {
    expect(shouldPreventSmoothScroll(document.createTextNode('x'))).toBe(false)
    expect(shouldPreventSmoothScroll(null)).toBe(false)
  })
})
