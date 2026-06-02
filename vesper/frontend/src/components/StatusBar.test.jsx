import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'
import StatusBar from './StatusBar.jsx'

const status = {
  integrations: { discord: { ready: true }, outlook: { ready: false } },
  vault: { online: true },
  memory: 'ok',
}

test('renders the wordmark and an entry per integration', () => {
  render(<StatusBar status={status} />)
  expect(screen.getByText('VESPER')).toBeInTheDocument()
  expect(screen.getByText('discord')).toBeInTheDocument()
  expect(screen.getByText('outlook')).toBeInTheDocument()
})

test('marks ready integrations on and not-ready off via data-state', () => {
  render(<StatusBar status={status} />)
  expect(screen.getByTestId('led-discord')).toHaveAttribute('data-state', 'on')
  expect(screen.getByTestId('led-outlook')).toHaveAttribute('data-state', 'off')
})
