import { useEffect } from 'react'
import Lenis from 'lenis'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

import 'lenis/dist/lenis.css'

import { shouldPreventSmoothScroll } from './preventSmoothScroll.js'

gsap.registerPlugin(ScrollTrigger)

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
 */

export function SmoothScrollProvider({ children }) {
  useEffect(() => {
    // Someone who asked the OS to stop animating means it. Native scrolling is
    // the accessible behaviour, so bail out before Lenis touches anything.
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)')
    if (reducedMotion.matches) return

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

    return () => {
      lenis.off('scroll', ScrollTrigger.update)
      gsap.ticker.remove(update)
      gsap.ticker.lagSmoothing(500, 33)
      lenis.destroy()
    }
  }, [])

  return children
}
