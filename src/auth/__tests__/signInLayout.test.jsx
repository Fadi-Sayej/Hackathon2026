// @vitest-environment jsdom

import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, fireEvent, screen } from '@testing-library/react'

import { renderWithI18n } from '../../test/renderWithI18n.jsx'
import { SignInLayout } from '../SignInLayout.jsx'
import { en } from '../../lib/i18n/dictionaries/en.js'
import { he } from '../../lib/i18n/dictionaries/he.js'

// The signed-out screen is a welcome, not the app with its nav taken out: the brand, a line
// on what SmartShelf does, and the sign-in card beside it.
afterEach(cleanup)

describe('the welcome around the sign-in card', () => {
  it('says what SmartShelf is for, and holds the card', () => {
    renderWithI18n(<SignInLayout><p data-testid="card">card</p></SignInLayout>, { language: 'en' })
    expect(screen.getByText(en['auth.welcome.headline'])).toBeTruthy()
    for (const key of ['auth.welcome.today', 'auth.welcome.prices', 'auth.welcome.orders']) {
      expect(screen.getByText(en[key])).toBeTruthy()
    }
    expect(screen.getByTestId('card')).toBeTruthy()
  })

  it('keeps the language switch, and switching it changes the words', () => {
    renderWithI18n(<SignInLayout><p>card</p></SignInLayout>, { language: 'en' })
    fireEvent.change(screen.getByLabelText(en['app.language']), { target: { value: 'he' } })
    expect(screen.getByText(he['auth.welcome.headline'])).toBeTruthy()
  })

  it('offers no page of the app before sign-in', () => {
    renderWithI18n(<SignInLayout><p>card</p></SignInLayout>, { language: 'en' })
    expect(screen.queryByRole('navigation')).toBeNull()
  })
})
