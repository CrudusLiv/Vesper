import { useCallback, useEffect, useRef } from 'react'
import { useStore } from '../state/store.jsx'
import { api, AuthError, clearSecret } from '../api/client.js'
import { useSpeech } from './useSpeech.js'

const STATUS_INTERVAL_MS = 15000

export function useVesper() {
  const { state, dispatch } = useStore()
  const speech = useSpeech()
  const gotTranscriptRef = useRef(false)

  // A 401 means the stored secret is bad/stale: clear it so a reload doesn't
  // re-adopt it, then drop the UI back to the unlock gate.
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

  const sendChat = useCallback(async (content, { spoken = false } = {}) => {
    const history = state.chat.messages.map((m) => ({ role: m.role, content: m.content }))
    dispatch({ type: 'CHAT_SEND', content, ts: Date.now() })
    try {
      const { reply, sources } = await api.chat(content, history)
      dispatch({ type: 'CHAT_REPLY', reply, sources, ts: Date.now() })
      if (spoken && speech.ttsSupported) {
        speech.speak(reply, {
          onStart: () => dispatch({ type: 'SET_ORB', orb: 'speaking' }),
          onEnd: () => dispatch({ type: 'SET_ORB', orb: 'idle' }),
        })
      } else {
        dispatch({ type: 'SET_ORB', orb: 'idle' })
      }
    } catch (err) {
      if (err instanceof AuthError) { lock(); return }
      dispatch({ type: 'CHAT_ERROR', error: 'Vesper is unavailable right now.', ts: Date.now() })
    }
  }, [state.chat.messages, dispatch, lock, speech])

  const search = useCallback(async (query) => {
    dispatch({ type: 'MEMORY_QUERY', query })
    if (!query.trim()) { dispatch({ type: 'MEMORY_RESULTS', results: [] }); return }
    dispatch({ type: 'MEMORY_LOADING' })
    try {
      const { results } = await api.search(query, 8)
      dispatch({ type: 'MEMORY_RESULTS', results })
    } catch (err) {
      if (err instanceof AuthError) lock()
      else dispatch({ type: 'MEMORY_ERROR', error: 'search failed' })
    }
  }, [dispatch, lock])

  const startVoice = useCallback(() => {
    if (!speech.sttSupported) return
    speech.cancelSpeech()
    gotTranscriptRef.current = false
    dispatch({ type: 'SET_ORB', orb: 'listening' })
    speech.startListening(
      (text) => { gotTranscriptRef.current = true; sendChat(text, { spoken: true }) },
      {
        onEnd: () => { if (!gotTranscriptRef.current) dispatch({ type: 'SET_ORB', orb: 'idle' }) },
        onError: () => dispatch({ type: 'SET_ORB', orb: 'idle' }),
      },
    )
  }, [speech, dispatch, sendChat])

  const stopVoice = useCallback(() => {
    speech.stopListening()
    dispatch({ type: 'SET_ORB', orb: 'idle' })
  }, [speech, dispatch])

  useEffect(() => {
    refreshStatus()
    const id = setInterval(refreshStatus, STATUS_INTERVAL_MS)
    return () => clearInterval(id)
  }, [refreshStatus])

  return { sendChat, search, refreshStatus, startVoice, stopVoice, sttSupported: speech.sttSupported }
}
