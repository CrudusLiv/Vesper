import { useState, useEffect, useRef, useCallback } from 'react'
import { Upload, Clock, CheckCircle2, XCircle } from 'lucide-react'
import './panels.css'

const OBSIDIAN_VAULT = 'Memory'
const obsidianHref = (path) =>
  `obsidian://open?vault=${OBSIDIAN_VAULT}&file=${encodeURIComponent(path)}`
const TERMINAL = new Set(['done', 'failed'])
const POLL_MS = 2500

function StatusBadge({ status }) {
  const map = {
    queued:     { icon: <Clock size={10} />,         label: 'Queued' },
    processing: { icon: <Clock size={10} />,         label: 'Processing…' },
    done:       { icon: <CheckCircle2 size={10} />,  label: 'Done' },
    failed:     { icon: <XCircle size={10} />,       label: 'Failed — retry' },
  }
  const entry = map[status] || { icon: null, label: status }
  return (
    <span className={`upload-badge ${status}`}>
      {entry.icon}{entry.label}
    </span>
  )
}

export default function UploadPanel({ onUpload, onListUploads }) {
  const [uploads, setUploads] = useState([])
  const [error, setError]     = useState('')
  const timer = useRef(null)

  const refresh = useCallback(async () => {
    const list = await onListUploads()
    if (list) setUploads(list)
    return list
  }, [onListUploads])

  useEffect(() => {
    const anyPending = uploads.some((u) => !TERMINAL.has(u.status))
    if (anyPending && !timer.current) {
      timer.current = setInterval(() => { refresh().catch(() => {}) }, POLL_MS)
    } else if (!anyPending && timer.current) {
      clearInterval(timer.current); timer.current = null
    }
    return () => { if (timer.current) { clearInterval(timer.current); timer.current = null } }
  }, [uploads, refresh])

  useEffect(() => { refresh().catch(() => {}) }, [refresh])

  async function onPick(e) {
    const file = e.target.files && e.target.files[0]
    e.target.value = ''
    if (!file) return
    setError('')
    try {
      const r = await onUpload(file)
      if (!r) return
      await refresh()
    } catch {
      setError('Upload failed')
    }
  }

  return (
    <div className="panel">
      <label className="upload-dropzone">
        <Upload size={20} style={{ opacity: 0.6 }} />
        <span className="upload-dropzone-text">Drop a file or click to choose</span>
        <span className="upload-dropzone-hint">.pptx · .pdf</span>
        <input
          data-testid="upload-input"
          type="file"
          accept=".pptx,.pdf"
          onChange={onPick}
          style={{ display: 'none' }}
        />
      </label>

      {error && <p className="panel-err">{error}</p>}

      {uploads.length > 0 && (
        <div className="upload-list">
          {uploads.map((u) => (
            <div key={u.id} className="upload-item">
              {u.status === 'done' && u.note_path ? (
                <a href={obsidianHref(u.note_path)} className="upload-item-name">
                  {u.category ? `${u.category} — ` : ''}{u.title || u.filename}
                </a>
              ) : (
                <span className="upload-item-name">{u.filename}</span>
              )}
              <StatusBadge status={u.status} />
            </div>
          ))}
        </div>
      )}

      {uploads.length === 0 && (
        <p className="panel-hint" style={{ textAlign: 'center' }}>
          Uploaded lectures appear here. Done files link to their Obsidian note.
        </p>
      )}
    </div>
  )
}
