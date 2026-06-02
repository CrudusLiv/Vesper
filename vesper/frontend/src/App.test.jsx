import { render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import App from './App.jsx'
import * as client from './api/client.js'

afterEach(() => { vi.restoreAllMocks(); localStorage.clear() })

test('shows the unlock gate when no secret is stored', () => {
  render(<App />)
  expect(screen.getByPlaceholderText(/api secret/i)).toBeInTheDocument()
})

test('boots into the dashboard when a secret is already stored', async () => {
  localStorage.setItem('vesper_secret', 'k')
  vi.spyOn(client.api, 'status').mockResolvedValue({ integrations: {}, vault: {}, memory: 'ok' })
  render(<App />)
  expect(await screen.findByText('VESPER')).toBeInTheDocument()
})
