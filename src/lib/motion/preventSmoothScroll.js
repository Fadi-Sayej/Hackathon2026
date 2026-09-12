/**
 * Its own module on purpose: SmoothScrollProvider registers a GSAP plugin at import
 * time, which needs a real browser. A pure predicate behind that cannot be tested, and
 * this one earns a test — it is the rule that decides whether a panel scrolls.
 */

/**
 * Should Lenis keep its hands off the wheel for this element?
 *
 * Taking over the wheel for the document also takes it from every scrollable
 * element inside it. The sidebar has `overflow-y: auto` and enough entries to
 * need it, and with smooth wheel on it simply stopped scrolling — the wheel
 * events went to the window instead. The same would happen to the wide tables
 * and the report modal.
 *
 * Detected rather than listed. A rule that names four class names is wrong the
 * first time someone adds a fifth scroll container, and the symptom — a panel
 * that silently will not scroll — is not one anybody connects back to a smooth
 * scrolling library.
 *
 * `data-lenis-prevent` stays supported as an explicit opt-out for anything this
 * cannot detect.
 */
export function shouldPreventSmoothScroll(node) {
  if (!node || node.nodeType !== 1) return false
  if (node.hasAttribute?.('data-lenis-prevent')) return true

  const style = node.ownerDocument?.defaultView?.getComputedStyle?.(node)
  if (!style) return false

  const scrollsVertically = style.overflowY === 'auto' || style.overflowY === 'scroll'
  const scrollsHorizontally = style.overflowX === 'auto' || style.overflowX === 'scroll'

  // Overflow alone is not enough: `overflow: auto` on an element with nothing to
  // scroll should not steal the wheel from the page behind it.
  if (scrollsVertically && node.scrollHeight > node.clientHeight) return true
  if (scrollsHorizontally && node.scrollWidth > node.clientWidth) return true
  return false
}
