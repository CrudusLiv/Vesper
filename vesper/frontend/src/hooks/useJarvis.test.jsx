import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, test, vi } from 'vitest'
import { StoreProvider, useStore } from '../state/store.jsx'
import { useJarvis } from './useJarvis.js'
import * as client from '../api/client.js'

afterEach(() => { vi.restoreAllMocks() })

function Harness() {
  const { state } = useStore()
  const { sendChat } = useJarvis()
  return (
    <div>
      <button onClick={() => sendChat('hi')}>send</button>
      <span data-testid="orb">{state.orb}</span>
      <span data-testid="unlocked">{String(state.auth.unlocked)}</span>
      <span data-testid="count">{state.chat.messages.length}</span>
      <span data-testid="last">{state.chat.messages.at(-1)?.content ?? ''}</span>
    </div>
  )
}

test('sendChat pushes user msg, calls api, then pushes the reply', async () => {
  vi.spyOn(client.api, 'status').mockResolvedValue({ integrations: {}, vault: {}, memory: 'ok' })
  vi.spyOn(client.api, 'chat').mockResolvedValue({ reply: 'yo', sources: [] })
  render(<StoreProvider><Harness /></StoreProvider>)
  await userEvent.click(screen.getByText('send'))
  await waitFor(() => expect(screen.getByTestId('count')).toHaveTextContent('2'))
  expect(screen.getByTestId('last')).toHaveTextContent('yo')
})

test('sendChat on LlmError pushes an error message and idles orb', async () => {
  vi.spyOn(client.api, 'status').mockResolvedValue({ integrations: {}, vault: {}, memory: 'ok' })
  vi.spyOn(client.api, 'chat').mockRejectedValue(new client.LlmError('llm unavailable'))
  render(<StoreProvider><Harness /></StoreProvider>)
  await userEvent.click(screen.getByText('send'))
  await waitFor(() => expect(screen.getByTestId('last')).toHaveTextContent(/unavailable/i))
  expect(screen.getByTestId('orb')).toHaveTextContent('idle')
})

test('a 401 from the status poll clears the stored secret and locks', async () => {
  localStorage.setItem('vesper_secret', 'stale')
  vi.spyOn(client.api, 'status').mockRejectedValue(new client.AuthError())
  render(<StoreProvider><Harness /></StoreProvider>)
  await waitFor(() => expect(screen.getByTestId('unlocked')).toHaveTextContent('false'))
  expect(localStorage.getItem('vesper_secret')).toBeNull()
})
