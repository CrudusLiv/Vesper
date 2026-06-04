import { renderHook, act, waitFor } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { useFeed } from './useFeed.js'
import * as clientModule from '../api/client.js'
import { StoreProvider } from '../state/store.jsx'

const wrapper = ({ children }) => <StoreProvider>{children}</StoreProvider>

const ITEM_UNREAD = { id: 'a1', kind: 'deadline_24h', title: '[CS101] Lab', body: 'due x', priority: 'high', read: false, created_at: '2026-06-04T09:00:00+08:00' }
const ITEM_READ   = { ...ITEM_UNREAD, id: 'a2', read: true }

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  vi.spyOn(clientModule.api, 'getFeed').mockResolvedValue([ITEM_UNREAD, ITEM_READ])
  vi.spyOn(clientModule.api, 'markFeedItemRead').mockResolvedValue({ ...ITEM_UNREAD, read: true })
  localStorage.setItem('vesper_secret', 'tok')
})
afterEach(() => { vi.restoreAllMocks(); vi.useRealTimers() })

describe('useFeed', () => {
  it('fetches on mount and populates items', async () => {
    const { result } = renderHook(() => useFeed(), { wrapper })
    await waitFor(() => expect(result.current.items).toHaveLength(2))
    expect(result.current.unreadCount).toBe(1)
  })

  it('polls again after 60 s', async () => {
    renderHook(() => useFeed(), { wrapper })
    await waitFor(() => expect(clientModule.api.getFeed).toHaveBeenCalledTimes(1))
    act(() => { vi.advanceTimersByTime(60_000) })
    await waitFor(() => expect(clientModule.api.getFeed).toHaveBeenCalledTimes(2))
  })

  it('markRead optimistically sets read=true then confirms via API', async () => {
    const { result } = renderHook(() => useFeed(), { wrapper })
    await waitFor(() => expect(result.current.items).toHaveLength(2))
    act(() => { result.current.markRead('a1') })
    expect(result.current.items.find(i => i.id === 'a1').read).toBe(true)
    await waitFor(() => expect(clientModule.api.markFeedItemRead).toHaveBeenCalledWith('a1'))
  })

  it('reverts optimistic read on API error', async () => {
    vi.spyOn(clientModule.api, 'markFeedItemRead').mockRejectedValue(new Error('500'))
    const { result } = renderHook(() => useFeed(), { wrapper })
    await waitFor(() => expect(result.current.items).toHaveLength(2))
    await act(async () => { result.current.markRead('a1') })
    await waitFor(() => expect(result.current.items.find(i => i.id === 'a1').read).toBe(false))
  })
})
