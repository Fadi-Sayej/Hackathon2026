import { useState } from 'react'

import { Button } from '../components/shared/Button.jsx'
import { useI18n } from '../lib/i18n/index.js'
import './auth.css'

/** An email inside Arabic or Hebrew text, isolated so it reads left to right. */
const isolate = (email) => `⁨${email ?? ''}⁩`

function GoogleMark() {
  return (
    <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9 3.5l6.7-6.7C35.6 2.4 30.2 0 24 0 14.6 0 6.6 5.4 2.7 13.3l7.8 6C12.4 13.6 17.7 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.1 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.4c-.5 2.9-2.2 5.3-4.6 6.9l7.4 5.7c4.3-4 6.9-9.9 6.9-17.1z" />
      <path fill="#FBBC05" d="M10.5 28.7c-.5-1.4-.8-3-.8-4.7s.3-3.2.8-4.7l-7.8-6C1 16.6 0 20.2 0 24s1 7.4 2.7 10.7l7.8-6z" />
      <path fill="#34A853" d="M24 48c6.2 0 11.4-2 15.2-5.5l-7.4-5.7c-2 1.4-4.7 2.3-7.8 2.3-6.3 0-11.6-4.1-13.5-9.8l-7.8 6C6.6 42.6 14.6 48 24 48z" />
    </svg>
  )
}

/**
 * The sign-in screens (ADR-029 §5), as the repository owner approved them on 2026-09-25:
 * sign in with Google or an email link; the link-sent confirmation; an account that has no
 * role. `needEmail` is the email link opened on a device that did not ask for it: the same
 * card with only the address, to finish rather than to send another link.
 */
export function SignInPage({
  status, email = null, error = false,
  onGoogle, onSendLink, onFinish, onUseDifferentEmail, onSignOut,
}) {
  const { t } = useI18n()
  const [typed, setTyped] = useState(email ?? '')

  if (status === 'loading') return <p className="spine__loading">{t('spine.loading')}</p>

  if (status === 'linkSent') {
    return (
      <section className="auth-card">
        <h1>{t('auth.linkSent.title')}</h1>
        <p>{t('auth.linkSent.body', { email: isolate(email) })}</p>
        <Button tone="ghost" className="auth-card__full" onClick={onUseDifferentEmail}>
          {t('auth.linkSent.other')}
        </Button>
      </section>
    )
  }

  if (status === 'noAccess') {
    return (
      <section className="auth-card">
        <h1>{t('auth.noAccess.title')}</h1>
        <p>{t('auth.noAccess.body', { email: isolate(email) })}</p>
        <Button tone="ghost" className="auth-card__full" onClick={onSignOut}>
          {t('auth.noAccess.signOut')}
        </Button>
      </section>
    )
  }

  const finishing = status === 'needEmail'
  const submit = (event) => {
    event.preventDefault()
    const address = typed.trim()
    if (!address) return
    if (finishing) onFinish(address)
    else onSendLink(address)
  }

  return (
    <section className="auth-card">
      <h1>{t('auth.signin.title')}</h1>
      {finishing ? null : <p>{t('auth.signin.lead')}</p>}
      {error ? <p role="alert" className="auth-card__error">{t('auth.error')}</p> : null}
      {finishing ? null : (
        <>
          <Button tone="ghost" className="auth-card__full" onClick={onGoogle}>
            <GoogleMark />
            <span>{t('auth.signin.google')}</span>
          </Button>
          <div className="auth-card__or">{t('auth.signin.or')}</div>
        </>
      )}
      <form onSubmit={submit} noValidate>
        <label className="auth-card__label" htmlFor="auth-email">{t('auth.signin.email')}</label>
        <input
          id="auth-email"
          className="auth-card__input"
          type="email"
          dir="ltr"
          autoComplete="email"
          placeholder="name@example.com"
          value={typed}
          onChange={(event) => setTyped(event.target.value)}
        />
        <Button tone="primary" type="submit" className="auth-card__full">
          {finishing ? t('auth.signin.title') : t('auth.signin.sendLink')}
        </Button>
      </form>
    </section>
  )
}

/**
 * The line at the top of the owner's app when a team account is looking at it (ADR-029 §5),
 * with the team's way to its own page. Only a team account ever renders this, so the owner
 * never sees the button, and the edge gate refuses him the page regardless.
 */
export function TeamBanner() {
  const { t } = useI18n()
  return (
    <div role="status" className="team-banner">
      <span>{t('auth.team.banner')}</span>
      <a className="btn btn-ghost team-banner__button" href="/telemetry.html">{t('auth.team.toTelemetry')}</a>
    </div>
  )
}
