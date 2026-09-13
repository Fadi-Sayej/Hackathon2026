import { useEffect } from 'react'

import { shouldPreventSmoothScroll } from './preventSmoothScroll.js'

/**
 * Smooth scrolling for the whole document.
 *
 * Lenis takes over the wheel and turns it into an interpolated scroll position.
 * That breaks ScrollTrigger on its own: ScrollTrigger listens to the native
 * `scroll` event, which Lenis no longer fires on every frame. So the two are
 * wired together below — Lenis reports its position to ScrollTrigger, and GSAP's
 * ticker drives Lenis instead of Lenis running its own requestAnimationFrame.
 * One clock, one frame, no tearing between an animation and the scroll it
 * belongs to.
 *
 * The app scrolls on the window, not on an inner element, so no `wrapper` or
 * `content` option is needed here. If a page ever scrolls inside a div, that
 * page needs its own Lenis instance rather than a change to this one.
 *
 * Nested scrollers are a different matter and are handled by `prevent` below.
 *
 * WHY GSAP AND LENIS LOAD ON DEMAND (2026-09-13)
 *   They were static imports, which put ~129 KB — a quarter of the owner's
 *   entire 496 KB download — in front of the first screen, and `registerPlugin`
 *   ran at import time so ScrollTrigger could not be tree-shaken. None of it is
 *   needed to read today's work, and on a machine set to reduce motion none of
 *   it is needed at all, yet it was fetched and parsed regardless.
 *
 *   So the machinery is imported inside the effect, after the reduced-motion
 *   check. `children` still renders synchronously — this component returns them
 *   directly and never gated them behind Suspense — so nothing about the first
 *   paint waits on the import. Smooth scrolling simply attaches a moment later,
 *   which is the correct trade for a scroll enhancement.
 */

export function SmoothScrollProvider({ children }) {
  useEffect(() => {
    // Someone who asked the OS to stop animating means it. Native scrolling is
    // the accessible behaviour, so bail out before Lenis is even fetched.
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)')
    if (reducedMotion.matches) return undefined

    // Set by the cleanup below. The import is async, so the component can
    // unmount before it resolves; without this the listeners would be attached
    // to a torn-down tree and never removed.
    let cancelled = false
    let detach = null

    Promise.all([
      import('lenis'),
      import('gsap'),
      import('gsap/ScrollTrigger'),
      import('lenis/dist/lenis.css'),
    ])
      .then(([{ default: Lenis }, { default: gsap }, { ScrollTrigger }]) => {
        if (cancelled) return

        gsap.registerPlugin(ScrollTrigger)

        const lenis = new Lenis({
          // GSAP's ticker calls `raf` below; Lenis must not also run its own loop.
          autoRaf: false,
          duration: 1.1,
          smoothWheel: true,
          prevent: shouldPreventSmoothScroll,
        })

        const update = (time) => lenis.raf(time * 1000)

        lenis.on('scroll', ScrollTrigger.update)
        gsap.ticker.add(update)

        // GSAP drops to a fixed step after a long frame, which makes scroll
        // position jump when a tab regains focus. Scroll should never lag-smooth.
        gsap.ticker.lagSmoothing(0)

        detach = () => {
          lenis.off('scroll', ScrollTrigger.update)
          gsap.ticker.remove(update)
          gsap.ticker.lagSmoothing(500, 33)
          lenis.destroy()
        }
      })
      .catch(() => {
        // A scroll enhancement that fails to load must not take the screen with
        // it. The document still scrolls natively.
      })

    return () => {
      cancelled = true
      if (detach) detach()
    }
  }, [])

  return children
}
