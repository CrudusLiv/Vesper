import { useRef, useEffect, useState } from 'react'
import { useAgent } from '../hooks/useAgent.js'
import { useVoice } from '../hooks/useVoice.js'
import ToolPalette from './ToolPalette.jsx'
import './CommandCenter.css'

export default function CommandCenter({ onToolSelect }) {
  const { messages, pending, toolCalls, toolResults, send } = useAgent()
  const [text, setText] = useState('')
  const [ttsEnabled, setTtsEnabled] = useState(false)
  const bottomRef = useRef(null)

  const voice = useVoice({
    onTranscript: (t) => send(t),
  })

  useEffect(() => {
    bottomRef.current?.scrollIntoView?.({ behavior: 'smooth' })
  }, [messages, pending])

  function submit(e) {
    e.preventDefault()
    const trimmed = text.trim()
    if (!trimmed) return
    if (ttsEnabled && voice.ttsSupported) {
      send(trimmed).then?.(() => {})
    } else {
      send(trimmed)
    }
    setText('')
  }

  function handleMic() {
    if (voice.listening) {
      voice.stopListening()
    } else {
      voice.startListening()
    }
  }

  function handleToolSelect(toolName) {
    const prefills = {
      notes: 'Add a note: ',
      finance: 'Log expense: ',
      schedule: 'Add to schedule: ',
      search: 'Search for: ',
    }
    if (prefills[toolName]) {
      setText(prefills[toolName])
    }
    if (onToolSelect) onToolSelect(toolName)
  }

  const lastToolCallIdx = messages.length - 1

  return (
    <div className="command-center">
      <div className="cc-messages" role="log" aria-live="polite">
        {messages.length === 0 && (
          <div className="cc-empty">Ask Vesper anything — or use a tool below.</div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`cc-msg cc-msg--${m.role}${m.error ? ' cc-msg--error' : ''}`}>
            <span className="cc-msg-content">{m.content}</span>
            {m.role === 'assistant' && m.sources?.length > 0 && (
              <span className="cc-msg-sources">▸ {m.sources.length} sources</span>
            )}
            {m.role === 'assistant' && i === lastToolCallIdx && toolCalls.length > 0 && (
              <div className="cc-tool-calls">
                {toolCalls.map((tc, j) => (
                  <div key={j} className="cc-tool-call">
                    <span className="cc-tool-name">{tc.tool_name}</span>
                    {toolResults[j] && (
                      <span className={`cc-tool-result ${toolResults[j].result?.success === false ? 'cc-tool-result--err' : 'cc-tool-result--ok'}`}>
                        {toolResults[j].result?.result ?? toolResults[j].result?.error ?? '✓'}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
        {pending && <div className="cc-thinking">thinking…</div>}
        <div ref={bottomRef} />
      </div>

      <ToolPalette onSelect={handleToolSelect} />

      <form className="cc-input-row" onSubmit={submit}>
        <input
          className="cc-input mono"
          placeholder="message Vesper…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          aria-label="message input"
        />
        <button
          type="button"
          className={`cc-btn-icon ${voice.listening ? 'cc-btn-icon--active' : ''}`}
          onClick={handleMic}
          disabled={!voice.sttSupported}
          aria-label="voice input"
          aria-pressed={voice.listening}
          title={voice.sttSupported ? (voice.listening ? 'Stop' : 'Speak') : 'Voice not supported'}
        >
          ◉
        </button>
        {voice.ttsSupported && (
          <button
            type="button"
            className={`cc-btn-icon ${ttsEnabled ? 'cc-btn-icon--active' : ''}`}
            onClick={() => setTtsEnabled(v => !v)}
            aria-label="toggle voice output"
            aria-pressed={ttsEnabled}
            title={ttsEnabled ? 'Voice output on' : 'Voice output off'}
          >
            ♪
          </button>
        )}
        <button type="submit" className="cc-btn-send" disabled={!text.trim()}>
          Send
        </button>
      </form>
    </div>
  )
}
