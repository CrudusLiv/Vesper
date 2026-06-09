import { Search } from 'lucide-react'
import './panels.css'

const OBSIDIAN_VAULT = 'Memory'
const obsidianHref = (path) =>
  `obsidian://open?vault=${OBSIDIAN_VAULT}&file=${encodeURIComponent(path)}`

export default function MemoryPanel({ results, onSearch }) {
  return (
    <div className="panel">
      <div className="panel-search-wrap">
        <span className="panel-search-icon">
          <Search size={13} />
        </span>
        <input
          className="panel-input panel-search-input"
          placeholder="search vault…"
          onChange={(e) => onSearch(e.target.value)}
        />
      </div>

      <div className="memory-results">
        {results.length === 0 && (
          <div className="panel-empty">
            <Search size={22} style={{ opacity: 0.25, marginBottom: 4 }} />
            Type to search your vault
          </div>
        )}
        {results.map((r, i) => (
          <a key={i} href={obsidianHref(r.path)} className="memory-result">
            <div className="memory-result-path">{r.path}</div>
            {r.heading && (
              <div className="memory-result-heading">{r.heading}</div>
            )}
            {r.content && (
              <div className="memory-result-body">
                {r.content.slice(0, 160)}
              </div>
            )}
          </a>
        ))}
      </div>
    </div>
  )
}
