// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, screen } from '@testing-library/react'

import { renderWithI18n } from '../../test/renderWithI18n.jsx'
import { SignInPage } from '../SignInPage.jsx'
import { ar } from '../../lib/i18n/dictionaries/ar.js'
import { en } from '../../lib/i18n/dictionaries/en.js'

// The screens approved on 2026-09-25 (ADR-029 §5): sign in with Google or an email link,
// the link-sent confirmation, and the account with no role. Each is checked for the
// approved wording and for calling the right handler.

afterEach(cleanup)

const handlers = () => ({
  onGoogle: vi.fn(), onSendLink: vi.fn(), onFinish: vi.fn(), onUseDifferentEmail: vi.fn(), onSignOut: vi.fn(),
  onPassword: vi.fn(), onResetPassword: vi.fn(),
})
const type = (label, value) => fireEvent.change(screen.getByLabelText(label), { target: { value } })

describe('sign in', () => {
  it('offers Google and an email link, in Arabic by default', () => {
    renderWithI18n(<SignInPage status="signedOut" {...handlers()} />)
    expect(screen.getByRole('heading', { name: ar['auth.signin.title'] })).toBeTruthy()
    expect(screen.getByRole('button', { name: ar['auth.signin.google'] })).toBeTruthy()
    expect(screen.getByRole('button', { name: ar['auth.signin.sendLink'] })).toBeTruthy()
    expect(screen.getByLabelText(ar['auth.signin.email'])).toBeTruthy()
  })

  it('starts Google sign-in', () => {
    const h = handlers()
    renderWithI18n(<SignInPage status="signedOut" {...h} />, { language: 'en' })
    fireEvent.click(screen.getByRole('button', { name: en['auth.signin.google'] }))
    expect(h.onGoogle).toHaveBeenCalledOnce()
  })

  it('sends the link to the address typed, trimmed', () => {
    const h = handlers()
    renderWithI18n(<SignInPage status="signedOut" {...h} />, { language: 'en' })
    fireEvent.change(screen.getByLabelText(en['auth.signin.email']), { target: { value: ' owner@example.com ' } })
    fireEvent.click(screen.getByRole('button', { name: en['auth.signin.sendLink'] }))
    expect(h.onSendLink).toHaveBeenCalledWith('owner@example.com')
  })

  it('says so when sign-in failed', () => {
    renderWithI18n(<SignInPage status="signedOut" error {...handlers()} />, { language: 'en' })
    expect(screen.getByRole('alert').textContent).toBe(en['auth.error'])
  })

  it('says why, when Firebase says why', () => {
    renderWithI18n(<SignInPage status="signedOut" error="auth/popup-blocked" {...handlers()} />, { language: 'en' })
    expect(screen.getByRole('alert').textContent).toBe(en['auth.error.popup'])
  })

  it('on an address sign-in does not accept, links to the one it does', () => {
    renderWithI18n(<SignInPage status="signedOut" error="auth/unauthorized-domain" siteAddress="shop.example.app"
      {...handlers()} />, { language: 'en' })
    const link = screen.getByRole('link', { name: 'shop.example.app' })
    expect(link.getAttribute('href')).toBe('https://shop.example.app/')
    expect(screen.getByRole('alert').textContent).toContain('shop.example.app')
  })

  it('on such an address, with no known address to send to, still says why', () => {
    renderWithI18n(<SignInPage status="signedOut" error="auth/unauthorized-domain" {...handlers()} />, { language: 'en' })
    expect(screen.getByRole('alert').textContent).toBe(en['auth.error.addressUnknown'])
  })

  it('says who can open it, under the card', () => {
    renderWithI18n(<SignInPage status="signedOut" {...handlers()} />, { language: 'en' })
    expect(screen.getByText(en['auth.signin.note'])).toBeTruthy()
  })
})

describe('after the link is sent', () => {
  it('names the address and offers another', () => {
    const h = handlers()
    renderWithI18n(<SignInPage status="linkSent" email="owner@example.com" {...h} />, { language: 'en' })
    expect(screen.getByRole('heading', { name: en['auth.linkSent.title'] })).toBeTruthy()
    expect(document.body.textContent).toContain('owner@example.com')
    fireEvent.click(screen.getByRole('button', { name: en['auth.linkSent.other'] }))
    expect(h.onUseDifferentEmail).toHaveBeenCalledOnce()
  })
})

describe('a link opened on another device', () => {
  it('asks for the address to finish, and does not send another link', () => {
    const h = handlers()
    renderWithI18n(<SignInPage status="needEmail" {...h} />, { language: 'en' })
    expect(screen.queryByRole('button', { name: en['auth.signin.google'] })).toBeNull()
    fireEvent.change(screen.getByLabelText(en['auth.signin.email']), { target: { value: 'owner@example.com' } })
    fireEvent.click(screen.getByRole('button', { name: en['auth.signin.title'] }))
    expect(h.onFinish).toHaveBeenCalledWith('owner@example.com')
    expect(h.onSendLink).not.toHaveBeenCalled()
  })
})

describe('an account with no role', () => {
  it('names the account and offers to sign out', () => {
    const h = handlers()
    renderWithI18n(<SignInPage status="noAccess" email="someone@example.com" {...h} />, { language: 'en' })
    expect(screen.getByRole('heading', { name: en['auth.noAccess.title'] })).toBeTruthy()
    expect(document.body.textContent).toContain('someone@example.com')
    fireEvent.click(screen.getByRole('button', { name: en['auth.noAccess.signOut'] }))
    expect(h.onSignOut).toHaveBeenCalledOnce()
  })
})


describe('email and password (the repository owner, 2026-10-03)', () => {
  it('signs in with the address and password typed', () => {
    const h = handlers()
    renderWithI18n(<SignInPage status="signedOut" {...h} />, { language: 'en' })
    type(en['auth.signin.email'], ' owner@example.com ')
    type(en['auth.signin.password'], 'a password')
    fireEvent.click(screen.getByRole('button', { name: en['auth.signin.title'] }))
    expect(h.onPassword).toHaveBeenCalledWith('owner@example.com', 'a password')
    expect(h.onSendLink).not.toHaveBeenCalled()
  })

  it('asks for the password rather than trying without one', () => {
    const h = handlers()
    renderWithI18n(<SignInPage status="signedOut" {...h} />, { language: 'en' })
    type(en['auth.signin.email'], 'owner@example.com')
    fireEvent.click(screen.getByRole('button', { name: en['auth.signin.title'] }))
    expect(h.onPassword).not.toHaveBeenCalled()
    expect(screen.getByRole('alert').textContent).toBe(en['auth.error.noPassword'])
  })

  it('sends a link to set or reset the password, to the address typed', () => {
    const h = handlers()
    renderWithI18n(<SignInPage status="signedOut" {...h} />, { language: 'en' })
    type(en['auth.signin.email'], 'owner@example.com')
    fireEvent.click(screen.getByRole('button', { name: en['auth.signin.forgot'] }))
    expect(h.onResetPassword).toHaveBeenCalledWith('owner@example.com')
  })

  it('asks for the address before sending a password link', () => {
    const h = handlers()
    renderWithI18n(<SignInPage status="signedOut" {...h} />, { language: 'en' })
    fireEvent.click(screen.getByRole('button', { name: en['auth.signin.forgot'] }))
    expect(h.onResetPassword).not.toHaveBeenCalled()
    expect(screen.getByRole('alert').textContent).toBe(en['auth.error.email'])
  })

  it('after the password link is sent, names the address and goes back', () => {
    const h = handlers()
    renderWithI18n(<SignInPage status="resetSent" email="owner@example.com" {...h} />, { language: 'en' })
    expect(screen.getByRole('heading', { name: en['auth.resetSent.title'] })).toBeTruthy()
    expect(document.body.textContent).toContain('owner@example.com')
    fireEvent.click(screen.getByRole('button', { name: en['auth.resetSent.back'] }))
    expect(h.onUseDifferentEmail).toHaveBeenCalledOnce()
  })

  it('says a wrong password plainly', () => {
    renderWithI18n(<SignInPage status="signedOut" error="auth/invalid-credential" {...handlers()} />, { language: 'en' })
    expect(screen.getByRole('alert').textContent).toBe(en['auth.error.password'])
  })
})
