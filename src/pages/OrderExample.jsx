import { useState } from 'react'

import { loadOrderExample } from '../lib/dataAdapters/loadOrderExample.js'
import { useI18n } from '../lib/i18n/index.js'

/**
 * OrderExample.jsx — "See how this page looks" on the order pages, while they wait (D-29).
 *
 * The example is a test shop: public/examples/order-example.json, which
 * scripts/build_order_example.py builds from the order probe's fixture world. Nothing but this
 * preview reads it. It is fetched only when asked for, so it costs the bundle nothing.
 *
 * The preview is fenced off: a region labelled "Example", a banner at its top, an "Example" tag on
 * every card, and the page rendered read-only. What the owner presses there is never recorded.
 */
export function ExamplePreview({ load = loadOrderExample, render }) {
  const { t } = useI18n()
  const [state, setState] = useState({ status: 'closed', example: null })

  const open = async () => {
    setState({ status: 'loading', example: null })
    const result = await load()
    setState(result.status === 'ok' ? { status: 'open', example: result.example } : { status: 'error', example: null })
  }

  if (state.status === 'closed') {
    return (
      <p className="example__offer">
        <button type="button" className="btn btn-ghost example__open" onClick={open}>{t('example.open')}</button>
      </p>
    )
  }
  if (state.status === 'loading') return <p className="example__offer">{t('example.loading')}</p>
  if (state.status === 'error') return <p className="example__offer" role="status">{t('example.unavailable')}</p>

  return (
    // The label is also drawn on every card (pages.css), because the banner scrolls away and a
    // card seen on its own must still say it is an example.
    <section className="example" role="region" aria-label={t('example.label')}
      style={{ '--example-label': JSON.stringify(t('example.label')) }}>
      <div className="example__banner" role="note">
        <span>{t('example.banner')}</span>
        <button type="button" className="btn btn-ghost example__close" onClick={() => setState({ status: 'closed', example: null })}>
          {t('example.close')}
        </button>
      </div>
      {render(state.example)}
    </section>
  )
}
