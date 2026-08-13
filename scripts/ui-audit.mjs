#!/usr/bin/env node
/**
 * UI/UX audit — every page, every language, every breakpoint.
 *
 * Screenshots alone do not find a hundred bugs; a person looking at 108 images
 * misses the two-pixel clip and the 3.1:1 contrast every time. So this measures
 * first and photographs second: the DOM checks below catch what is mechanical
 * (overflow, clipping, touch targets, contrast, untranslated keys, elements
 * escaping the viewport), and the screenshots are there for what only an eye
 * catches — rhythm, alignment, whether a screen reads as one thing.
 *
 * Output:
 *   audit/findings.json   every finding, machine-readable
 *   audit/report.md       grouped and counted, for reading
 *   audit/shots/*.png     one per page × language × breakpoint
 *
 * Run with the dev server already up: node scripts/ui-audit.mjs
 */

import { chromium } from 'playwright-core'
import { mkdirSync, writeFileSync } from 'node:fs'

const BASE = process.env.AUDIT_BASE ?? 'http://localhost:5173'
const OUT = 'audit'

const PAGES = [
  'operational',
  'recommendations',
  'orders',
  'prices',
  'assortment',
  'store-layout',
  'shelf-plan',
  'products',
  'expiry',
  'dashboard',
  'report',
  'data-source',
]

const LANGUAGES = ['ar', 'he', 'en']

// A forecourt manager uses a phone behind the counter; the office laptop is the
// other real case. 1440 is the demo projector.
const VIEWPORTS = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'laptop', width: 1280, height: 800 },
  { name: 'mobile', width: 390, height: 844 },
]

/**
 * Everything below runs inside the page. Kept as one function so it is a single
 * round trip per screen rather than twenty.
 */
function collectFindings() {
  const out = []
  const add = (severity, rule, message, selector) =>
    out.push({ severity, rule, message, selector })

  const describe = (el) => {
    if (!el) return '?'
    const id = el.id ? `#${el.id}` : ''
    const cls = typeof el.className === 'string' && el.className
      ? `.${el.className.trim().split(/\s+/).slice(0, 2).join('.')}`
      : ''
    return `${el.tagName.toLowerCase()}${id}${cls}`
  }

  const text = (el) => (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 60)

  /**
   * Nearest ancestor that contains this element's horizontal overflow.
   *
   * getBoundingClientRect() reports the LAYOUT box, which is unaffected by an
   * ancestor's overflow — an element sitting 6px past the right edge of a
   * `overflow: hidden` container is reported at its full un-clipped width even
   * though the user can never see that part. Measuring against the viewport
   * alone therefore reports pixels that are not on screen.
   *
   * Two kinds of ancestor make an overhang a non-issue:
   *   - `auto` / `scroll` that is actually scrolling — reachable content
   *   - `hidden` / `clip` — content the browser has already cut off
   * Either way the element does not escape anything the user can see.
   */
  const clippingAncestor = (el) => {
    let node = el.parentElement
    while (node && node !== document.body) {
      const overflow = getComputedStyle(node).overflowX
      if (overflow === 'hidden' || overflow === 'clip') return node
      if ((overflow === 'auto' || overflow === 'scroll') && node.scrollWidth > node.clientWidth + 1) {
        return node
      }
      node = node.parentElement
    }
    return null
  }

  const visible = (el) => {
    const style = getComputedStyle(el)
    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false
    const rect = el.getBoundingClientRect()
    return rect.width > 0 && rect.height > 0
  }

  // ── 1. The page itself must not scroll sideways ────────────────────
  const doc = document.scrollingElement
  if (doc.scrollWidth > window.innerWidth + 1) {
    add(
      'high',
      'page-overflow-x',
      `Page scrolls horizontally: ${doc.scrollWidth}px content in a ${window.innerWidth}px viewport`,
      'html',
    )
  }

  const all = [...document.querySelectorAll('body *')].filter(visible)

  for (const el of all) {
    const style = getComputedStyle(el)
    const rect = el.getBoundingClientRect()

    // ── 2. Text clipped by its own box ───────────────────────────────
    // Only flag elements that actually hide the overflow, and only when the
    // element holds text of its own rather than laid-out children.
    const ownText = [...el.childNodes].some(
      (node) => node.nodeType === 3 && node.textContent.trim().length > 2,
    )
    const hidesX = style.overflowX === 'hidden' || style.overflow === 'hidden'
    if (ownText && hidesX && el.scrollWidth > el.clientWidth + 2 && style.textOverflow !== 'ellipsis') {
      add(
        'medium',
        'text-clipped',
        `Text is cut off with no ellipsis: "${text(el)}" (${el.scrollWidth}px in ${el.clientWidth}px)`,
        describe(el),
      )
    }

    // ── 2b. Text cut off by an ANCESTOR's overflow ───────────────────
    // The check above only sees an element that clips its own text. The worse
    // case is an element that overflows happily — `overflow: visible`, nothing
    // wrong with it in isolation — inside a parent that clips.
    //
    // That is exactly how "₪63,571.87" reached the screen as "₪63,57": the
    // value had visible overflow, the metric card had `overflow: hidden`, and
    // neither element on its own looked like a bug. A truncated number reads as
    // a smaller real number rather than as an error, which makes this the most
    // expensive kind of clipping to ship.
    if (ownText && !hidesX && rect.width > 0) {
      const range = document.createRange()
      range.selectNodeContents(el)
      const inkRight = Math.max(...[...range.getClientRects()].map((r) => r.right), 0)
      const inkLeft = Math.min(...[...range.getClientRects()].map((r) => r.left), Infinity)
      let node = el.parentElement
      while (node && node !== document.body) {
        const parentStyle = getComputedStyle(node)
        // Stop at the FIRST ancestor that manages the x-axis at all, not the
        // first one that clips. Walking past a scroller to reach a clipper
        // above it reports content the user can simply scroll to: at mobile the
        // nav is a horizontal scroll strip inside an `overflow: hidden` aside,
        // and skipping the strip flagged all 226 of its labels.
        if (parentStyle.overflowX === 'visible') {
          node = node.parentElement
          continue
        }
        if (parentStyle.overflowX === 'hidden' || parentStyle.overflowX === 'clip') {
          const box = node.getBoundingClientRect()
          if (inkRight > box.right + 1 || inkLeft < box.left - 1) {
            add(
              'high',
              'text-cut-by-ancestor',
              `Text is cut off by an ancestor's overflow: "${text(el)}" (ink ${Math.round(inkLeft)}–${Math.round(inkRight)} in a ${Math.round(box.left)}–${Math.round(box.right)} box)`,
              `${describe(el)} inside ${describe(node)}`,
            )
          }
        }
        // `auto` or `scroll`: the overhang is reachable, so it is not cut off.
        break
      }
    }

    // ── 3. Anything escaping its own scroll container ────────────────
    // Measured against the nearest ancestor that actually scrolls, not the
    // window. A table row inside `overflow-x: auto` legitimately extends past
    // the viewport — the first version of this check reported 503 of those and
    // buried everything real underneath them.
    if (rect.width > 0 && style.position !== 'fixed' && !clippingAncestor(el)) {
      if (rect.right > window.innerWidth + 2 || rect.left < -2) {
        add(
          'high',
          'escapes-viewport',
          `Extends past the viewport with no scroll container (left ${Math.round(rect.left)}, right ${Math.round(rect.right)}, viewport ${window.innerWidth})`,
          describe(el),
        )
      }
    }

    // ── 4. Touch targets ─────────────────────────────────────────────
    const interactive =
      el.matches('button, a, select, input:not([type=hidden]), [role=button], [tabindex]:not([tabindex="-1"])')
    if (interactive && (rect.height < 24 || rect.width < 24)) {
      add(
        'medium',
        'touch-target',
        `Interactive element is ${Math.round(rect.width)}×${Math.round(rect.height)}px — below the 24px minimum`,
        `${describe(el)} "${text(el)}"`,
      )
    }

    // ── 5. An interactive element with no accessible name ────────────
    if (interactive && !text(el) && !el.getAttribute('aria-label') && !el.getAttribute('title')) {
      const hasImage = el.querySelector('img[alt]:not([alt=""]), svg[aria-label]')
      // An input's textContent is always empty; its name comes from a wrapping
      // or associated <label>. Ignoring that flagged every correctly-labelled
      // field in the app.
      const labelled =
        el.closest('label') ||
        (el.id && document.querySelector(`label[for="${CSS.escape(el.id)}"]`)) ||
        el.getAttribute('aria-labelledby') ||
        el.getAttribute('placeholder')
      if (!hasImage && !labelled) {
        add('medium', 'no-accessible-name', 'Interactive element has no text, aria-label or title', describe(el))
      }
    }

    // ── 6. Untranslated keys leaking to the screen ───────────────────
    if (ownText) {
      const raw = text(el)
      if (/\b(nav|page|common|op|sl|sp|pg|gap|exp|dash|rep|ds|ord|rec|prod|prov|photo|plan|pgm)\.[a-zA-Z]{3,}\b/.test(raw)) {
        add('high', 'untranslated-key', `Raw translation key on screen: "${raw}"`, describe(el))
      }
    }
  }

  // ── 7. Contrast ────────────────────────────────────────────────────
  // Only for elements holding their own text, against the nearest painted
  // ancestor background — a naive check flags every transparent wrapper.
  const luminance = (rgb) => {
    const [r, g, b] = rgb.map((value) => {
      const channel = value / 255
      return channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4
    })
    return 0.2126 * r + 0.7152 * g + 0.0722 * b
  }
  const parse = (value) => {
    const match = value.match(/rgba?\(([^)]+)\)/)
    if (!match) return null
    const parts = match[1].split(',').map((piece) => parseFloat(piece))
    if (parts.length === 4 && parts[3] < 0.9) return null
    return parts.slice(0, 3)
  }
  /**
   * Nearest painted background, or null when a gradient is in the way.
   *
   * `background: linear-gradient(...)` leaves `backgroundColor` transparent, so
   * walking past it finds the page behind and reports white-on-white at 1.00:1.
   * Every primary button was flagged that way. A gradient cannot be sampled from
   * computed style, so the honest answer is "cannot judge" rather than a wrong
   * number — the fallback-colour check below covers the real risk instead.
   */
  const backgroundOf = (el) => {
    let node = el
    while (node && node !== document.documentElement) {
      const style = getComputedStyle(node)
      if (style.backgroundImage && style.backgroundImage !== 'none') return null
      const rgb = parse(style.backgroundColor)
      if (rgb) return rgb
      node = node.parentElement
    }
    return [255, 255, 255]
  }

  for (const el of all) {
    const ownText = [...el.childNodes].some(
      (node) => node.nodeType === 3 && node.textContent.trim().length > 2,
    )
    if (!ownText) continue
    const style = getComputedStyle(el)
    const fg = parse(style.color)
    if (!fg) continue
    const bg = backgroundOf(el)
    if (!bg) continue
    const lighter = Math.max(luminance(fg), luminance(bg))
    const darker = Math.min(luminance(fg), luminance(bg))
    const ratio = (lighter + 0.05) / (darker + 0.05)

    const size = parseFloat(style.fontSize)
    const bold = parseInt(style.fontWeight, 10) >= 700
    const large = size >= 24 || (size >= 18.66 && bold)
    const required = large ? 3 : 4.5

    if (ratio < required) {
      add(
        ratio < required - 1 ? 'high' : 'medium',
        'contrast',
        `Contrast ${ratio.toFixed(2)}:1 against ${required}:1 required at ${size}px — "${text(el)}"`,
        describe(el),
      )
    }
  }

  // ── 8. Tiny text ───────────────────────────────────────────────────
  for (const el of all) {
    const ownText = [...el.childNodes].some(
      (node) => node.nodeType === 3 && node.textContent.trim().length > 2,
    )
    if (!ownText) continue
    const size = parseFloat(getComputedStyle(el).fontSize)
    if (size < 11) {
      add('low', 'tiny-text', `Font size ${size}px is below the 11px floor — "${text(el)}"`, describe(el))
    }
  }

  // ── 9. A gradient with no background-color fallback ────────────────
  // If the gradient does not paint — forced-colors mode, print, an old engine —
  // the text is left on whatever is behind it. One declaration prevents it.
  for (const el of all) {
    const style = getComputedStyle(el)
    if (!style.backgroundImage || style.backgroundImage === 'none') continue
    if (!style.backgroundImage.includes('gradient')) continue
    // Any explicitly declared background-color counts as the fallback, including
    // a translucent wash — the author has stated what should be underneath. Only
    // a fully transparent box is actually unprotected. `parse()` rejects low
    // alpha for contrast maths, which is a different question.
    const declared = style.backgroundColor && !/rgba\([^)]*,\s*0\s*\)/.test(style.backgroundColor)
      && style.backgroundColor !== 'transparent'
    if (!declared && text(el)) {
      add(
        'medium',
        'gradient-no-fallback',
        `Gradient background with no background-color fallback under text "${text(el)}"`,
        describe(el),
      )
    }
  }

  // ── 10. Numbers and money broken across lines ──────────────────────
  // "₪63,571.87" rendering as "₪63,5" / "71.87" is not a wrap, it is a wrong
  // number. Detected by measuring the rendered line boxes of a numeric string.
  for (const el of all) {
    const raw = (el.textContent || '').trim()
    if (!/[\d]/.test(raw)) continue
    const ownText = [...el.childNodes].some((node) => node.nodeType === 3 && node.textContent.trim())
    if (!ownText) continue
    // A single run of digits/separators/currency, i.e. one number.
    if (!/^[^\p{L}]*[\d][\d.,\s\u2066-\u2069₪%+-]*$/u.test(raw)) continue
    const range = document.createRange()
    range.selectNodeContents(el)
    // Count LINES, not rects. A bidi-isolated number inside right-to-left text
    // produces several client rects on one line — counting rects reported 150
    // wrapped numbers that were rendering perfectly.
    const lines = new Set([...range.getClientRects()].map((rect) => Math.round(rect.top))).size
    if (lines > 1) {
      add('high', 'number-wrapped', `A single number is split across ${lines} lines: "${raw.slice(0, 40)}"`, describe(el))
    }
  }

  // ── 11. Latin sentences inside a right-to-left interface ───────────
  // Not a style problem: it means the string never reached the dictionaries.
  const dir = document.documentElement.dir
  if (dir === 'rtl') {
    // Product names, barcodes and supplier names come from the till and are
    // deliberately never translated — flagging them buries the real findings.
    // Anything inside these carries data, not interface text.
    const DATA_TEXT = [
      '[data-product-name]', '.product-name', '.cell-hebrew', '.table-cell-hebrew',
      '.hebrew-text', 'td', 'th', '.pg-position-label', '.pg-tip-name',
      '.recommendation-product', '.op-handled-row', 'code', 'pre', '[dir="auto"]',
    ].join(',')

    for (const el of all) {
      if (el.closest(DATA_TEXT)) continue
      const own = [...el.childNodes]
        .filter((node) => node.nodeType === 3)
        .map((node) => node.textContent.trim())
        .join(' ')
        .trim()
      if (own.length < 12) continue
      const words = own.split(/\s+/)
      const latin = words.filter((word) => /^[A-Za-z][A-Za-z'’,.-]*$/.test(word))
      // Three or more plain Latin words is prose, not a brand or a unit.
      if (latin.length >= 3 && latin.length / words.length > 0.6) {
        add('high', 'untranslated-text', `English prose in an RTL interface: "${own.slice(0, 70)}"`, describe(el))
      }
    }

    // ── 11b. Single English words in controls and labels ─────────────
    // The prose rule above needs three Latin words and twelve characters, which
    // is right for a paragraph and blind to interface chrome: "Done",
    // "Dismiss", "Later" and "at stake" shipped untranslated on every Arabic
    // and Hebrew screen and the audit reported nothing. Buttons and labels are
    // written by us, never by the till, so a Latin one is untranslated — the
    // few genuine exceptions are named below.
    const LATIN_BY_DESIGN = new Set([
      'smartshelf ai', 'smartshelf', 'ai', 'csv', 'comax', 'wolt', 'pos', 'sku',
      'default', 'ils', 'llm', 'mcp', 'api', 'json', 'parquet', 'kaggle',
    ])
    for (const el of all) {
      // `label > span` is in the list because that is how an entire form hid:
      // every field in the receiving form put its caption in a span inside the
      // label, so the label's own text was empty and nothing was reported while
      // "Barcode", "Quantity *" and "Supplier *" sat there in English.
      const CONTROL_TEXT =
        'button, label, label > span, .eyebrow, .metric-label, [class*="-label"], option, legend, [placeholder]'
      if (!el.matches(CONTROL_TEXT)) continue
      if (el.closest(DATA_TEXT)) continue
      const own = [...el.childNodes]
        .filter((node) => node.nodeType === 3)
        .map((node) => node.textContent.trim())
        .join(' ')
        .trim()
      if (own.length < 2) continue
      if (LATIN_BY_DESIGN.has(own.toLowerCase())) continue
      // Entirely Latin letters, spaces and light punctuation — no Hebrew or
      // Arabic anywhere in it.
      if (/^[A-Za-z][A-Za-z\s'’,.&+·/-]*$/.test(own)) {
        add('high', 'untranslated-control', `Untranslated control or label in an RTL interface: "${own.slice(0, 50)}"`, describe(el))
      }
    }
  }

  return out
}

// ── Driver ───────────────────────────────────────────────────────────
mkdirSync(`${OUT}/shots`, { recursive: true })

const browser = await chromium.launch({ channel: 'chrome' })
const findings = []
let shots = 0

for (const viewport of VIEWPORTS) {
  const context = await browser.newContext({
    viewport: { width: viewport.width, height: viewport.height },
    deviceScaleFactor: 2,
  })
  const page = await context.newPage()

  const consoleErrors = []
  page.on('pageerror', (error) => consoleErrors.push(String(error)))
  // Chrome's console message for a failed fetch is "Failed to load resource:
  // the server responded with a status of 404 ()" — no URL, which makes the
  // finding unactionable. The response event carries the URL, so record that.
  page.on('response', (response) => {
    if (response.status() >= 400) {
      consoleErrors.push(`HTTP ${response.status()} — ${response.url()}`)
    }
  })
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text())
  })

  for (const language of LANGUAGES) {
    await page.goto(BASE, { waitUntil: 'networkidle' })
    await page.waitForTimeout(1200)
    await page.selectOption('.lang-switch-select', language).catch(() => {})
    await page.waitForTimeout(500)

    for (const [index, id] of PAGES.entries()) {
      consoleErrors.length = 0
      const nav = page.locator('.nav-item').nth(index)
      await nav.scrollIntoViewIfNeeded().catch(() => {})
      await nav.click({ timeout: 5000 }).catch(() => {})
      await page.waitForTimeout(900)

      const label = `${id}__${language}__${viewport.name}`
      // Not fullPage: the Products table renders 7,451 rows and a full-page
      // capture of it crashed the renderer, taking the whole run with it. The
      // viewport shot plus the DOM measurements below is what actually finds
      // bugs; a 40,000px tall image finds none.
      await page
        .screenshot({ path: `${OUT}/shots/${label}.png` })
        .then(() => { shots += 1 })
        .catch((error) => {
          findings.push({
            severity: 'high', rule: 'screenshot-failed', selector: '-',
            message: `Could not capture ${label}: ${String(error).slice(0, 120)}`,
            page: id, language, viewport: viewport.name,
          })
        })

      let found = []
      try {
        found = await page.evaluate(collectFindings)
      } catch (error) {
        // A page that kills the renderer is itself the finding.
        findings.push({
          severity: 'high', rule: 'page-crashed', selector: '-',
          message: `Audit could not run on this screen: ${String(error).slice(0, 140)}`,
          page: id, language, viewport: viewport.name,
        })
        if (page.isClosed()) break
      }
      for (const finding of found) findings.push({ ...finding, page: id, language, viewport: viewport.name })
      for (const error of consoleErrors) {
        findings.push({
          severity: 'high',
          rule: 'console-error',
          message: error.slice(0, 200),
          selector: '-',
          page: id,
          language,
          viewport: viewport.name,
        })
      }
    }
  }

  await context.close()
}

await browser.close()

// ── Report ───────────────────────────────────────────────────────────
// Collapse identical findings: the same clipped label on 36 screens is one bug,
// and a list that repeats it 36 times hides the other 99.
const grouped = new Map()
for (const finding of findings) {
  const key = `${finding.rule}::${finding.selector}::${finding.message.slice(0, 80)}`
  if (!grouped.has(key)) grouped.set(key, { ...finding, occurrences: 0, pages: new Set(), languages: new Set(), viewports: new Set() })
  const entry = grouped.get(key)
  entry.occurrences += 1
  entry.pages.add(finding.page)
  entry.languages.add(finding.language)
  entry.viewports.add(finding.viewport)
}

const unique = [...grouped.values()].map((entry) => ({
  severity: entry.severity,
  rule: entry.rule,
  message: entry.message,
  selector: entry.selector,
  occurrences: entry.occurrences,
  pages: [...entry.pages].sort(),
  languages: [...entry.languages].sort(),
  viewports: [...entry.viewports].sort(),
}))

const rank = { high: 0, medium: 1, low: 2 }
unique.sort((a, b) => rank[a.severity] - rank[b.severity] || b.occurrences - a.occurrences)

writeFileSync(`${OUT}/findings.json`, JSON.stringify(unique, null, 2))

const byRule = new Map()
for (const finding of unique) byRule.set(finding.rule, (byRule.get(finding.rule) ?? 0) + 1)

const lines = [
  '# UI/UX audit',
  '',
  `${shots} screenshots · ${findings.length} raw findings · **${unique.length} distinct issues**`,
  '',
  '| Rule | Distinct issues |',
  '|---|---:|',
  ...[...byRule.entries()].sort((a, b) => b[1] - a[1]).map(([rule, count]) => `| ${rule} | ${count} |`),
  '',
  '## Issues',
  '',
]
for (const [index, finding] of unique.entries()) {
  lines.push(
    `### ${index + 1}. [${finding.severity}] ${finding.rule}`,
    '',
    `- **${finding.message}**`,
    `- selector: \`${finding.selector}\``,
    `- ${finding.occurrences} occurrence(s) · pages: ${finding.pages.join(', ')} · languages: ${finding.languages.join(', ')} · viewports: ${finding.viewports.join(', ')}`,
    '',
  )
}
writeFileSync(`${OUT}/report.md`, lines.join('\n'))

console.log(`\n${shots} screenshots written to ${OUT}/shots/`)
console.log(`${findings.length} raw findings → ${unique.length} distinct issues`)
for (const [rule, count] of [...byRule.entries()].sort((a, b) => b[1] - a[1])) {
  console.log(`  ${String(count).padStart(4)}  ${rule}`)
}
console.log(`\nReport: ${OUT}/report.md\n`)
