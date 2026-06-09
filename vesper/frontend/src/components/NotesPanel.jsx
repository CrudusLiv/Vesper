import { useState } from 'react'
import { Check } from 'lucide-react'
import './panels.css'

export default function NotesPanel({ onSave }) {
  const [text, setText]   = useState('')
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
      setError('Could not save note')
    }
  }

  return (
    <div className="panel">
      <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <textarea
          className="panel-textarea"
          placeholder="Note to self…"
          value={text}
          rows={5}
          onChange={(e) => { setText(e.target.value); setSaved(false) }}
        />
        <button type="submit" disabled={!text.trim()} className="panel-btn">
          Save note
        </button>
      </form>

      {saved && (
        <p className="panel-ok">
          <Check size={13} /> Saved to vault
        </p>
      )}
      {error && <p className="panel-err">{error}</p>}
    </div>
  )
}
