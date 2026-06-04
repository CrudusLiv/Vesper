import { useState, useEffect } from 'react'
import { ConflictError } from '../api/client.js'

export default function SchedulePanel({ onLoad, onSave }) {
  const [current, setCurrent] = useState(null)
  const [text, setText] = useState('')
  const [conflict, setConflict] = useState(null) // { summary, exists }
  const [status, setStatus] = useState('')

  useEffect(() => {
    onLoad().then((r) => { if (r) setCurrent(r.schedule) }).catch(() => {})
  }, [onLoad])

  async function save(confirm) {
    if (!text.trim()) return
    setStatus('')
    try {
      const r = await onSave(text, confirm)
      if (!r) return
      setConflict(null); setText(''); setStatus('saved')
      const fresh = await onLoad()
      if (fresh) setCurrent(fresh.schedule)
    } catch (err) {
      if (err instanceof ConflictError) { setConflict(err.data); return }
      setStatus('could not parse timetable')
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: 10 }}>
      <div style={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--dim)' }}>Schedule</div>
      <pre className="mono" style={{ fontSize: 10, color: 'var(--dim)', whiteSpace: 'pre-wrap', margin: 0 }}>
        {current || 'no schedule set yet'}
      </pre>
      <form onSubmit={(e) => { e.preventDefault(); save(false) }} style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <textarea
          className="mono"
          placeholder="paste your timetable…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={4}
          style={{ background: '#0b0f15', border: '1px solid var(--line)', borderRadius: 6, padding: '6px 8px', fontSize: 12, color: 'var(--ink)', resize: 'vertical' }}
        />
        <button type="submit" disabled={!text.trim()} style={{ background: 'transparent', border: '1px solid var(--accent)', borderRadius: 6, padding: '6px 8px', fontSize: 12, color: 'var(--accent2)', cursor: text.trim() ? 'pointer' : 'not-allowed' }}>
          Set schedule
        </button>
      </form>
      {conflict && (
        <div style={{ border: '1px solid var(--led-off)', borderRadius: 6, padding: 8, display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div className="mono" style={{ fontSize: 10, color: 'var(--ink)' }}>A schedule already exists. Replace it with:</div>
          <pre className="mono" style={{ fontSize: 10, color: 'var(--dim)', whiteSpace: 'pre-wrap', margin: 0 }}>{conflict.summary}</pre>
          <div style={{ display: 'flex', gap: 6 }}>
            <button type="button" onClick={() => save(true)} style={{ background: 'var(--accent)', border: 'none', borderRadius: 5, padding: '4px 10px', fontSize: 11, color: '#fff', cursor: 'pointer' }}>Replace</button>
            <button type="button" onClick={() => setConflict(null)} style={{ background: 'transparent', border: '1px solid var(--line)', borderRadius: 5, padding: '4px 10px', fontSize: 11, color: 'var(--dim)', cursor: 'pointer' }}>Cancel</button>
          </div>
        </div>
      )}
      {status && <div className="mono" style={{ fontSize: 10, color: status === 'saved' ? 'var(--led-on)' : 'var(--led-off)' }}>{status}</div>}
    </div>
  )
}
