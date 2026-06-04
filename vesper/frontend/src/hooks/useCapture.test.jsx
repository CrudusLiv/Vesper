import { renderHook } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { StoreProvider } from '../state/store.jsx'
import { useCapture } from './useCapture.js'
import * as client from '../api/client.js'

const wrapper = ({ children }) => <StoreProvider>{children}</StoreProvider>

beforeEach(() => { localStorage.clear(); vi.restoreAllMocks() })
afterEach(() => { vi.restoreAllMocks() })

test('logFinance returns the api result', async () => {
  vi.spyOn(client.api, 'finance').mockResolvedValue({ month_total: 5 })
  const { result } = renderHook(() => useCapture(), { wrapper })
  await expect(result.current.logFinance(5, 'food', '')).resolves.toEqual({ month_total: 5 })
})

test('an AuthError clears the stored secret (locks)', async () => {
  client.setSecret('k')
  vi.spyOn(client.api, 'note').mockRejectedValue(new client.AuthError())
  const { result } = renderHook(() => useCapture(), { wrapper })
  await result.current.saveNote('x')
  expect(client.getSecret()).toBeNull()
})

test('a ConflictError propagates (not swallowed)', async () => {
  vi.spyOn(client.api, 'setSchedule').mockRejectedValue(new client.ConflictError({ summary: 'p', exists: true }))
  const { result } = renderHook(() => useCapture(), { wrapper })
  await expect(result.current.saveSchedule('x', false)).rejects.toBeInstanceOf(client.ConflictError)
})

test('uploadDocument returns the api result', async () => {
  vi.spyOn(client.api, 'uploadInbox').mockResolvedValue({ id: '1', status: 'queued' })
  const { result } = renderHook(() => useCapture(), { wrapper })
  const file = new File(['x'], 'a.pptx')
  await expect(result.current.uploadDocument(file)).resolves.toEqual({ id: '1', status: 'queued' })
  expect(client.api.uploadInbox).toHaveBeenCalledWith(file)
})

test('listUploads returns the api result', async () => {
  vi.spyOn(client.api, 'inboxUploads').mockResolvedValue([{ id: '1', status: 'done' }])
  const { result } = renderHook(() => useCapture(), { wrapper })
  await expect(result.current.listUploads()).resolves.toEqual([{ id: '1', status: 'done' }])
})

test('an AuthError during upload clears the stored secret (locks)', async () => {
  client.setSecret('k')
  vi.spyOn(client.api, 'uploadInbox').mockRejectedValue(new client.AuthError())
  const { result } = renderHook(() => useCapture(), { wrapper })
  await result.current.uploadDocument(new File(['x'], 'a.pptx'))
  expect(client.getSecret()).toBeNull()
})
