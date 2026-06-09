import { GripHorizontal, Minus, ChevronDown, ChevronRight } from 'lucide-react'
import { useDragPanel } from '../hooks/useDragPanel.js'
import './FloatingPanel.css'

export function FloatingPanel({ panelId, title, icon = '◻', children, defaultPosition = { x: 20, y: 20 }, onMinimize }) {
  const { position, isDragging, isCollapsed, startDrag, toggleCollapse } = useDragPanel(panelId, defaultPosition)

  return (
    <div
      className="floating-panel frosted-glass"
      data-collapsed={isCollapsed}
      data-dragging={isDragging}
      style={{ left: `${position.x}px`, top: `${position.y}px` }}
    >
      <div className="panel-header" onMouseDown={startDrag}>
        <span className="panel-drag-handle" aria-hidden="true">
          <GripHorizontal size={12} />
        </span>
        <h3 className="panel-title">{title}</h3>
        <div className="panel-controls">
          {onMinimize && (
            <button
              className="panel-ctrl-btn"
              onMouseDown={(e) => e.stopPropagation()}
              onClick={(e) => { e.stopPropagation(); onMinimize({ id: panelId, title, icon }) }}
              aria-label="Minimize to dock"
              title="Minimize to dock"
            >
              <Minus size={12} />
            </button>
          )}
          <button
            className="panel-ctrl-btn"
            onMouseDown={(e) => e.stopPropagation()}
            onClick={(e) => { e.stopPropagation(); toggleCollapse() }}
            aria-label={isCollapsed ? 'Expand panel' : 'Collapse panel'}
          >
            {isCollapsed ? <ChevronRight size={12} /> : <ChevronDown size={12} />}
          </button>
        </div>
      </div>

      {!isCollapsed && (
        <div className="panel-content">
          {children}
        </div>
      )}
    </div>
  )
}
