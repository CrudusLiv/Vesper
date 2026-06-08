// Obsidian vault name for deep-links. The vault on disk is Dynamous/Memory;
// Obsidian opens by vault NAME, which is the folder name "Memory". Change here
// if the user's Obsidian vault is registered under a different name.
const OBSIDIAN_VAULT = 'Memory'

function obsidianHref(path) {
  return `obsidian://open?vault=${OBSIDIAN_VAULT}&file=${encodeURIComponent(path)}`
}

export default function MemoryPanel({ results, onSearch }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: 10, height: '100%', borderRight: '1px solid var(--line)', background: 'rgba(13,17,23,0.5)' }}>
      <div style={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--dim)' }}>Memory</div>
      <input
        className="mono"
        placeholder="search vault…"
        onChange={(e) => onSearch(e.target.value)}
        style={{ background: '#0b0f15', border: '1px solid var(--line)', borderRadius: 6, padding: '6px 8px', fontSize: 14, color: 'var(--ink)' }}
      />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, overflow: 'auto' }}>
        {results.map((r, i) => (
          <a
            key={i}
            href={obsidianHref(r.path)}
            style={{ textDecoration: 'none', border: '1px solid var(--line)', borderLeft: '2px solid var(--accent)', borderRadius: 5, padding: '6px 8px' }}
          >
            <div className="mono" style={{ fontSize: 11, color: 'var(--accent2)' }}>{r.path}</div>
            {r.heading && (
              <div className="mono" style={{ fontSize: 11, color: 'var(--ink)', marginTop: 2 }}>{r.heading}</div>
            )}
            {r.content && (
              <div className="mono" style={{ fontSize: 11, color: 'var(--dim)', marginTop: 3, lineHeight: 1.4, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                {r.content.slice(0, 160)}
              </div>
            )}
            <div className="mono" style={{ fontSize: 10, color: 'var(--dim)', marginTop: 3, opacity: 0.6 }}>
              score {r.score}
            </div>
          </a>
        ))}
      </div>
    </div>
  )
}
