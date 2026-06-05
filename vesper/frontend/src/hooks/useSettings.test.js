import { renderHook, act, waitFor } from '@testing-library/react'
import { beforeEach, expect, test, vi } from 'vitest'
import { useSettings } from './useSettings.js'
import * as client from '../api/client.js'

beforeEach(() => {
  vi.restoreAllMocks()
})

test('loads settings on demand', async () => {
  const mockSettings = {
    active_hours_start: '09:00',
    active_hours_end: '22:00',
    heartbeat_interval_minutes: 30,
    features: { inbox: true },
  }
  vi.spyOn(client.api, 'getSettings').mockResolvedValue(mockSettings)

  const { result } = renderHook(() => useSettings())
  expect(result.current.settings).toBeNull()

  await act(async () => {
    await result.current.load()
  })

  expect(result.current.settings).toEqual(mockSettings)
  expect(result.current.error).toBeNull()
})

test('saves settings and updates state', async () => {
  const updated = { heartbeat_interval_minutes: 20 }
  const response = { ...updated, active_hours_start: '09:00' }
  vi.spyOn(client.api, 'saveSettings').mockResolvedValue(response)

  const { result } = renderHook(() => useSettings())

  await act(async () => {
    await result.current.save(updated)
  })

  expect(result.current.settings).toEqual(response)
  expect(client.api.saveSettings).toHaveBeenCalledWith(updated)
})

test('sets error on load failure', async () => {
  vi.spyOn(client.api, 'getSettings').mockRejectedValue(new Error('Network error'))

  const { result } = renderHook(() => useSettings())

  await act(async () => {
    await result.current.load()
  })

  expect(result.current.error).toBe('Network error')
  expect(result.current.settings).toBeNull()
})

test('sets error on save failure and re-throws', async () => {
  vi.spyOn(client.api, 'saveSettings').mockRejectedValue(new Error('Save failed'))

  const { result } = renderHook(() => useSettings())

  let thrownError
  await act(async () => {
    try {
      await result.current.save({ test: true })
    } catch (err) {
      thrownError = err
    }
  })

  expect(thrownError).toBeDefined()
  expect(thrownError.message).toBe('Save failed')
  expect(result.current.error).toBe('Save failed')
})

test('manages loading state during operations', async () => {
  vi.spyOn(client.api, 'getSettings').mockImplementation(
    () => new Promise(resolve => setTimeout(() => resolve({}), 10))
  )

  const { result } = renderHook(() => useSettings())

  expect(result.current.loading).toBe(false)

  await act(async () => {
    const loadPromise = result.current.load()
    await loadPromise
  })

  expect(result.current.loading).toBe(false)
})
