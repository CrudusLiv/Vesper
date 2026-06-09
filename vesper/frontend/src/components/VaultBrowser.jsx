import { useState, useEffect, useCallback } from 'react'
import { Folder, FileText, ChevronUp, RotateCcw, Trash2 } from 'lucide-react'
import './panels.css'

const OBSIDIAN_VAULT = 'Memory'
const obsidianHref = (path) =>
  `obsidian://open?vault=${OBSIDIAN_VAULT}&file=${encodeURIComponent(path)}`

export default function VaultBrowser({ onList, onDelete, onUndo }) {
  const [dir, setDir]         = useState('')
  const [entries, setEntries] = useState([])
  const [status, setStatus]   = useState('')

  const load = useCallback((d) => {
    onList(d)
      .then((r) => { if (r) { setDir(r.directory); setEntries(r.entries) } })
      .catch(() => setStatus('Cannot open folder'))
  }, [onList])

  useEffect(() => { load('') }, [load])

  const childPath = (name) => (dir ? `${dir}/${name}` : name)

  function up() {
    if (!dir) return
    const parts = dir.split('/'); parts.pop()
    load(parts.join('/'))
  }

  async function del(name) {
    try {
      const r = await onDelete(childPath(name))
      if (!r) return
      setStatus(`Moved to trash`)
      load(dir)
    } catch {
      setStatus('Delete failed')
    }
  }

  async function undo() {
    try {
      const r = await onUndo()
      if (!r) return
      setStatus(r.message)
      load(dir)
    } catch {
      setStatus('Undo failed')
    }
  }

  return (
    <div className="panel">
      <div className="vault-nav">
        <button
          type="button"
          onClick={up}
          disabled={!dir}
          className="panel-btn-ghost"
          aria-label="Go up"
        >
          <ChevronUp size={12} /> Up
        </button>
        <span className="vault-path">{dir || 'vault root'}</span>
        <button
          type="button"
          onClick={undo}
          className="panel-btn-ghost"
          aria-label="Undo last delete"
          title="Undo last delete"
        >
          <RotateCcw size={12} />
        </button>
      </div>

      <div className="vault-entries">
        {entries.length === 0 && (
          <div className="panel-empty">
            <Folder size={22} style={{ opacity: 0.25, marginBottom: 4 }} />
            Empty folder
          </div>
        )}
        {entries.map((e) => (
          <div key={e.name} className="vault-entry">
            <span className={`vault-entry-icon${e.is_dir ? ' is-dir' : ''}`}>
              {e.is_dir
                ? <Folder size={14} />
                : <FileText size={14} />
              }
            </span>
            {e.is_dir ? (
              <button
                type="button"
                className="vault-entry-name"
                onClick={() => load(childPath(e.name))}
                aria-label={e.name}
              >
                {e.name}
              </button>
            ) : (
              <>
                <a
                  href={obsidianHref(childPath(e.name))}
                  className="vault-entry-name"
                >
                  {e.name}
                </a>
                <button
                  type="button"
                  className="panel-btn-danger"
                  onClick={() => del(e.name)}
                  aria-label={`Delete ${e.name}`}
                  title="Move to trash"
                >
                  <Trash2 size={11} />
                </button>
              </>
            )}
          </div>
        ))}
      </div>

      {status && <p className="panel-hint">{status}</p>}
    </div>
  )
}
