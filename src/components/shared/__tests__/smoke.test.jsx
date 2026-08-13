// @vitest-environment jsdom

/**
 * Proves the component-test path actually works: jsdom is active, React 19
 * renders, Testing Library queries resolve, and user-event drives an interaction.
 *
 * This project runs vitest under `node` by default. Component tests opt in with
 * the docblock on line 1 of this file — copy it into any new .test.jsx.
 */

import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { Button } from '../Button.jsx'

// Auto-cleanup only fires when vitest globals are enabled, and they are not.
afterEach(cleanup)

describe('component test infrastructure', () => {
  it('has a DOM', () => {
    expect(typeof document).toBe('object')
  })

  it('renders a shared component and finds it by role', () => {
    render(<Button tone="primary">Save</Button>)
    expect(screen.getByRole('button', { name: 'Save' })).toBeDefined()
  })

  it('drives a click through user-event', async () => {
    const onClick = vi.fn()
    render(<Button tone="primary" onClick={onClick}>Save</Button>)
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(onClick).toHaveBeenCalledTimes(1)
  })
})
