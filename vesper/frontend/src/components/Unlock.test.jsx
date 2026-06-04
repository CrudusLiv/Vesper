import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, test, vi } from 'vitest'
import Unlock from './Unlock.jsx'
import * as client from '../api/client.js'

afterEach(() => { vi.restoreAllMocks(); localStorage.clear() })

test('valid secret probes status, stores it, and calls onUnlock', async () => {
  vi.spyOn(client.api, 'status').mockResolvedValue({ memory: 'ok' })
  const onUnlock = vi.fn()
  render(<Unlock onUnlock={onUnlock} />)
  await userEvent.type(screen.getByPlaceholderText(/secret/i), 'goodsecret')
  await userEvent.click(screen.getByRole('button', { name: /unlock/i }))
  expect(client.api.status).toHaveBeenCalledWith('goodsecret')
  expect(onUnlock).toHaveBeenCalledWith('goodsecret')
})

test('wrong secret shows an error and does not unlock', async () => {
  vi.spyOn(client.api, 'status').mockRejectedValue(new client.AuthError())
  const onUnlock = vi.fn()
  render(<Unlock onUnlock={onUnlock} />)
  await userEvent.type(screen.getByPlaceholderText(/secret/i), 'bad')
  await userEvent.click(screen.getByRole('button', { name: /unlock/i }))
  expect(await screen.findByText(/incorrect secret/i)).toBeInTheDocument()
  expect(onUnlock).not.toHaveBeenCalled()
})
