import './ToolPalette.css'

const TOOLS = [
  { id: 'notes',    icon: '📝', label: 'Note' },
  { id: 'finance',  icon: '💰', label: 'Finance' },
  { id: 'schedule', icon: '📅', label: 'Schedule' },
  { id: 'search',   icon: '🔍', label: 'Search' },
  { id: 'files',    icon: '📁', label: 'Files' },
  { id: 'browser',  icon: '🌐', label: 'Browser' },
  { id: 'system',   icon: '⚙', label: 'System' },
]

export default function ToolPalette({ onSelect }) {
  return (
    <div className="tool-palette" role="toolbar" aria-label="quick tools">
      {TOOLS.map(({ id, icon, label }) => (
        <button
          key={id}
          className="tp-btn"
          onClick={() => onSelect?.(id)}
          title={label}
          aria-label={label}
        >
          <span className="tp-btn-icon" aria-hidden="true">{icon}</span>
          <span className="tp-btn-label">{label}</span>
        </button>
      ))}
    </div>
  )
}
