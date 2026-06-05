import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'
import StatusBar from './StatusBar.jsx'

const status = {
  integrations: { discord: { ready: true }, outlook: { ready: false } },
  vault: { online: true },
  memory: 'ok',
}

test('renders the system title and an entry per integration', () => {
  render(<StatusBar status={status} />)
  expect(screen.getByText('System')).toBeInTheDocument()
  expect(screen.getByText('discord')).toBeInTheDocument()
  expect(screen.getByText('outlook')).toBeInTheDocument()
})

test('marks ready integrations on and not-ready off via data-ready attribute', () => {
  render(<StatusBar status={status} />)
  const discordStatus = screen.getByText('discord').closest('.status-item').querySelector('.status-icon')
  const outlookStatus = screen.getByText('outlook').closest('.status-item').querySelector('.status-icon')
  expect(discordStatus).toHaveAttribute('data-ready', 'true')
  expect(outlookStatus).toHaveAttribute('data-ready', 'false')
})

test('returns null when status is empty', () => {
  const { container } = render(<StatusBar status={{ integrations: {}, vault: {}, memory: 'ok' }} />)
  expect(container.firstChild).toBeNull()
})
