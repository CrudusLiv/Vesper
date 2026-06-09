import { useCallback, useState } from 'react'
import { useStore } from '../state/store.jsx'
import { api, AuthError, clearSecret } from '../api/client.js'

export function useAgent() {
  const { state, dispatch } = useStore()
  const [toolCalls, setToolCalls] = useState([])
  const [toolResults, setToolResults] = useState([])

  const lock = useCallback(() => {
    clearSecret()
    dispatch({ type: 'LOCK' })
  }, [dispatch])

  const send = useCallback(async (content) => {
    const history = state.chat.messages.map((m) => ({ role: m.role, content: m.content }))
    dispatch({ type: 'CHAT_SEND', content, ts: Date.now() })
    setToolCalls([])
    setToolResults([])
    try {
      const data = await api.chat(content, history)
      dispatch({ type: 'CHAT_REPLY', reply: data.reply, sources: data.sources, ts: Date.now() })
      if (data.tool_calls?.length) setToolCalls(data.tool_calls)
      if (data.tool_results?.length) setToolResults(data.tool_results)
    } catch (err) {
      if (err instanceof AuthError) { lock(); return }
      dispatch({ type: 'CHAT_ERROR', error: 'Vesper is unavailable right now.', ts: Date.now() })
    }
  }, [state.chat.messages, dispatch, lock])

  return {
    messages: state.chat.messages,
    pending: state.chat.pending,
    toolCalls,
    toolResults,
    send,
  }
}
