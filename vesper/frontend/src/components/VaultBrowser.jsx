import { useState, useEffect, useCallback } from 'react'

const OBSIDIAN_VAULT = 'Memory'
const obsidianHref = (path) => `obsidian://open?vault=${OBSIDIAN_VAULT}&file=${encodeURIComponent(path)}`

export default function VaultBrowser({ onList, onDelete, onUndo }) {
  const [dir, setDir] = useState('')
  const [entries, setEntries] = useState([])
  const [status, setStatus] = useState('')

  const load = useCallback((d) => {
    onList(d)
      .then((r) => { if (r) { setDir(r.directory); setEntries(r.entries) } })
      .catch(() => setStatus('cannot open folder'))
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
      setStatus(`moved to ${r.trash_path}`)
      load(dir)
    } catch {
      setStatus('delete failed')
    }
  }

  async function undo() {
    try {
      const r = await onUndo()
      if (!r) return
      setStatus(r.message)
      load(dir)
    } catch {
      setStatus('undo failed')
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: 10 }}>
      <div style={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--dim)' }}>Files</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <button type="button" onClick={up} disabled={!dir} style={{ fontSize: 10, padding: '2px 6px', background: 'transparent', border: '1px solid var(--line)', borderRadius: 4, color: 'var(--dim)', cursor: dir ? 'pointer' : 'default' }}>↑ up</button>
        <span className="mono" style={{ fontSize: 10, color: 'var(--accent2)' }}>{dir || 'vault root'}</span>
        <button type="button" onClick={undo} style={{ marginLeft: 'auto', fontSize: 10, padding: '2px 6px', background: 'transparent', border: '1px solid var(--line)', borderRadius: 4, color: 'var(--dim)', cursor: 'pointer' }}>undo</button>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, overflow: 'auto' }}>
        {entries.map((e) => (
          <div key={e.name} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            {e.is_dir ? (
              <button type="button" aria-label={e.name} onClick={() => load(childPath(e.name))} className="mono" style={{ flex: 1, textAlign: 'left', fontSize: 11, background: 'transparent', border: 'none', color: 'var(--ink)', cursor: 'pointer' }}>📁 {e.name}</button>
            ) : (
              <>
                <a href={obsidianHref(childPath(e.name))} className="mono" style={{ flex: 1, fontSize: 11, color: 'var(--ink)', textDecoration: 'none' }}>📄 {e.name}</a>
                <button type="button" aria-label={`delete ${e.name}`} onClick={() => del(e.name)} style={{ fontSize: 10, padding: '1px 6px', background: 'transparent', border: '1px solid var(--led-off)', borderRadius: 4, color: 'var(--led-off)', cursor: 'pointer' }}>✕</button>
              </>
            )}
          </div>
        ))}
      </div>
      {status && <div className="mono" style={{ fontSize: 10, color: 'var(--dim)' }}>{status}</div>}
    </div>
  )
}
