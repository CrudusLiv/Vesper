import { useState, useEffect, useRef, useCallback } from 'react'
import { useStore } from '../state/store.jsx'
import { api, AuthError, clearSecret } from '../api/client.js'

const POLL_MS = 60_000

export function useFeed() {
  const { dispatch } = useStore()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const timerRef = useRef(null)

  const lock = useCallback(() => {
    clearSecret()
    dispatch({ type: 'LOCK' })
  }, [dispatch])

  const fetchFeed = useCallback(async () => {
    try {
      const data = await api.getFeed()
      setItems(data)
      setError(null)
    } catch (err) {
      if (err instanceof AuthError) { lock(); return }
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [lock])

  useEffect(() => {
    fetchFeed()
    timerRef.current = setInterval(fetchFeed, POLL_MS)
    return () => clearInterval(timerRef.current)
  }, [fetchFeed])

  const markRead = useCallback(async (id) => {
    setItems(prev => prev.map(item => item.id === id ? { ...item, read: true } : item))
    try {
      await api.markFeedItemRead(id)
    } catch {
      setItems(prev => prev.map(item => item.id === id ? { ...item, read: false } : item))
    }
  }, [])

  const unreadCount = items.filter(i => !i.read).length

  return { items, unreadCount, markRead, loading, error }
}
