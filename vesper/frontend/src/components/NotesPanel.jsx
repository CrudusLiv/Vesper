import { useState } from 'react'

export default function NotesPanel({ onSave }) {
  const [text, setText] = useState('')
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  async function submit(e) {
    e.preventDefault()
    const t = text.trim()
    if (!t) return
    setError(''); setSaved(false)
    try {
      const r = await onSave(t)
      if (!r) return
      setSaved(true); setText('')
    } catch {
      setError('could not save note')
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: 10 }}>
      <div style={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--dim)' }}>Note</div>
      <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <textarea
          className="mono"
          placeholder="note to self…"
          value={text}
          onChange={(e) => { setText(e.target.value); setSaved(false) }}
          rows={4}
          style={{ background: '#0b0f15', border: '1px solid var(--line)', borderRadius: 6, padding: '6px 8px', fontSize: 12, color: 'var(--ink)', resize: 'vertical' }}
        />
        <button
          type="submit"
          disabled={!text.trim()}
          style={{ background: 'transparent', border: '1px solid var(--accent)', borderRadius: 6, padding: '6px 8px', fontSize: 12, color: 'var(--accent2)', cursor: text.trim() ? 'pointer' : 'not-allowed' }}
        >
          Save note
        </button>
      </form>
      {saved && <div className="mono" style={{ fontSize: 10, color: 'var(--led-on)' }}>saved ✓</div>}
      {error && <div className="mono" style={{ fontSize: 10, color: 'var(--led-off)' }}>{error}</div>}
    </div>
  )
}
