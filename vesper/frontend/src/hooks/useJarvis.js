import { useCallback, useEffect } from 'react'
import { useStore } from '../state/store.jsx'
import { api, AuthError, clearSecret } from '../api/client.js'

const STATUS_INTERVAL_MS = 15000
const SPEAKING_MS = 1500

export function useJarvis() {
  const { state, dispatch } = useStore()

  // A 401 means the stored secret is bad/stale: clear it from localStorage so
  // a reload doesn't re-adopt it, then drop the UI back to the unlock gate.
  const lock = useCallback(() => {
    clearSecret()
    dispatch({ type: 'LOCK' })
  }, [dispatch])

  const refreshStatus = useCallback(async () => {
    dispatch({ type: 'STATUS_LOADING' })
    try {
      const status = await api.status()
      dispatch({ type: 'STATUS_OK', status })
    } catch (err) {
      if (err instanceof AuthError) lock()
      else dispatch({ type: 'STATUS_ERROR', error: 'offline' })
    }
  }, [dispatch, lock])

  const sendChat = useCallback(async (content) => {
    const history = state.chat.messages.map((m) => ({ role: m.role, content: m.content }))
    dispatch({ type: 'CHAT_SEND', content, ts: Date.now() })
    try {
      const { reply, sources } = await api.chat(content, history)
      dispatch({ type: 'CHAT_REPLY', reply, sources, ts: Date.now() })
      setTimeout(() => dispatch({ type: 'SET_ORB', orb: 'idle' }), SPEAKING_MS)
    } catch (err) {
      if (err instanceof AuthError) { lock(); return }
      dispatch({ type: 'CHAT_ERROR', error: 'Vesper is unavailable right now.', ts: Date.now() })
    }
  }, [state.chat.messages, dispatch, lock])

  const search = useCallback(async (query) => {
    dispatch({ type: 'MEMORY_QUERY', query })
    if (!query.trim()) { dispatch({ type: 'MEMORY_RESULTS', results: [] }); return }
    dispatch({ type: 'MEMORY_LOADING' })
    try {
      const { results } = await api.search(query, 5)
      dispatch({ type: 'MEMORY_RESULTS', results })
    } catch (err) {
      if (err instanceof AuthError) lock()
      else dispatch({ type: 'MEMORY_ERROR', error: 'search failed' })
    }
  }, [dispatch, lock])

  useEffect(() => {
    refreshStatus()
    const id = setInterval(refreshStatus, STATUS_INTERVAL_MS)
    return () => clearInterval(id)
  }, [refreshStatus])

  return { sendChat, search, refreshStatus }
}
