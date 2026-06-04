import { useState, useEffect, useRef, useCallback } from 'react'

const OBSIDIAN_VAULT = 'Memory'
const obsidianHref = (path) => `obsidian://open?vault=${OBSIDIAN_VAULT}&file=${encodeURIComponent(path)}`
const TERMINAL = new Set(['done', 'failed'])
const POLL_MS = 2500

const STATUS_LABEL = {
  queued: '⏳ queued',
  processing: '⏳ processing',
  done: '✓ done',
  failed: '✗ failed — will retry automatically',
}

export default function UploadPanel({ onUpload, onListUploads }) {
  const [uploads, setUploads] = useState([])
  const [error, setError] = useState('')
  const timer = useRef(null)

  const refresh = useCallback(async () => {
    const list = await onListUploads()
    if (list) setUploads(list)
    return list
  }, [onListUploads])

  // Poll while any record is non-terminal; stop once all are done/failed.
  useEffect(() => {
    const anyPending = uploads.some((u) => !TERMINAL.has(u.status))
    if (anyPending && !timer.current) {
      timer.current = setInterval(() => { refresh().catch(() => {}) }, POLL_MS)
    } else if (!anyPending && timer.current) {
      clearInterval(timer.current)
      timer.current = null
    }
    return () => {
      if (timer.current) { clearInterval(timer.current); timer.current = null }
    }
  }, [uploads, refresh])

  useEffect(() => { refresh().catch(() => {}) }, [refresh])

  async function onPick(e) {
    const file = e.target.files && e.target.files[0]
    e.target.value = '' // allow re-selecting the same file
    if (!file) return
    setError('')
    try {
      const r = await onUpload(file)
      if (!r) return
      await refresh()
    } catch {
      setError('upload failed')
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: 10 }}>
      <div style={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--dim)' }}>Uploads</div>
      <label style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 4, padding: 14, borderRadius: 6, border: '1px dashed var(--accent)', color: 'var(--accent2)', cursor: 'pointer', fontSize: 11 }}>
        drop a .pptx / .pdf or click to choose
        <input
          data-testid="upload-input"
          type="file"
          accept=".pptx,.pdf"
          onChange={onPick}
          style={{ display: 'none' }}
        />
      </label>
      {error && <div className="mono" style={{ fontSize: 10, color: 'var(--led-off)' }}>{error}</div>}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, overflow: 'auto' }}>
        {uploads.map((u) => (
          <div key={u.id} className="mono" style={{ display: 'flex', flexDirection: 'column', gap: 2, fontSize: 10, padding: '4px 0', borderTop: '1px solid var(--line)' }}>
            {u.status === 'done' && u.note_path ? (
              <a href={obsidianHref(u.note_path)} style={{ color: 'var(--ink)', textDecoration: 'none' }}>
                ✓ {u.category ? `${u.category} — ` : ''}{u.title || u.filename}
              </a>
            ) : (
              <span style={{ color: 'var(--ink)' }}>{u.filename}</span>
            )}
            <span style={{ color: u.status === 'failed' ? 'var(--led-off)' : 'var(--dim)' }}>
              {STATUS_LABEL[u.status] || u.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
