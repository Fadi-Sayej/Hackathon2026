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
})

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
