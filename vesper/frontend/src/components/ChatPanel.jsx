import { useState } from 'react'

export default function ChatPanel({ messages, pending, onSend, voiceSupported = false, listening = false, onMic = () => {} }) {
  const [text, setText] = useState('')

  function submit(e) {
    e.preventDefault()
    const trimmed = text.trim()
    if (!trimmed) return
    onSend(trimmed)
    setText('')
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', borderLeft: '1px solid var(--line)', background: 'rgba(13,17,23,0.5)' }}>
      <div style={{ flex: 1, padding: 10, display: 'flex', flexDirection: 'column', gap: 8, overflow: 'auto' }}>
        {messages.map((m, i) => (
          <div
            key={i}
            style={{
              maxWidth: '88%', padding: '7px 9px', borderRadius: 8, fontSize: 13, lineHeight: 1.45,
              alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
              background: m.role === 'user' ? 'rgba(45,108,223,0.18)' : '#0c1118',
              border: `1px solid ${m.role === 'user' ? 'rgba(45,108,223,0.4)' : 'var(--line)'}`,
              color: m.error ? 'var(--led-off)' : 'var(--ink)',
            }}
          >
            {m.content}
            {m.role === 'assistant' && m.sources?.length > 0 && (
              <div className="mono" style={{ marginTop: 5, fontSize: 9, color: 'var(--dim)' }}>
                ▸ {m.sources.length} sources
              </div>
            )}
          </div>
        ))}
        {pending && <div className="mono" style={{ fontSize: 11, color: 'var(--dim)' }}>Vesper is thinking…</div>}
      </div>
      <form onSubmit={submit} style={{ borderTop: '1px solid var(--line)', padding: 8, display: 'flex', gap: 6 }}>
        <input
          className="mono"
          placeholder="message Vesper…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          style={{ flex: 1, background: '#0b0f15', border: '1px solid var(--line)', borderRadius: 6, padding: '6px 8px', fontSize: 12, color: 'var(--ink)' }}
        />
        <button
          type="button"
          onClick={onMic}
          disabled={!voiceSupported}
          aria-label="voice"
          aria-pressed={listening}
          title={voiceSupported ? (listening ? 'Stop listening' : 'Speak') : 'Voice not supported in this browser'}
          style={{
            width: 30, height: 30, borderRadius: '50%',
            border: `1px solid ${listening ? 'var(--accent2)' : 'var(--accent)'}`,
            background: listening ? 'var(--accent)' : 'transparent',
            color: listening ? '#fff' : 'var(--accent2)',
            cursor: voiceSupported ? 'pointer' : 'not-allowed',
          }}
        >
          ◉
        </button>
      </form>
    </div>
  )
}
