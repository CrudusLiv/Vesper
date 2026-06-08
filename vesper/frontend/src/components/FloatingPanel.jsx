import { useDragPanel } from '../hooks/useDragPanel.js';
import './FloatingPanel.css';

export function FloatingPanel({ panelId, title, icon = '◻', children, defaultPosition = { x: 20, y: 20 }, onMinimize }) {
  const { position, isDragging, isCollapsed, startDrag, toggleCollapse } = useDragPanel(panelId, defaultPosition);

  return (
    <div
      className="floating-panel frosted-glass"
      data-collapsed={isCollapsed}
      data-dragging={isDragging}
      style={{
        left: `${position.x}px`,
        top: `${position.y}px`,
      }}
    >
      <div className="panel-header" onMouseDown={startDrag}>
        <h3 className="panel-title">{title}</h3>
        {onMinimize && (
          <button
            className="panel-minimize"
            onClick={(e) => { e.stopPropagation(); onMinimize({ id: panelId, title, icon }); }}
            aria-label="Minimize to dock"
            title="Minimize to dock"
          >
            ◂
          </button>
        )}
        <button
          className="panel-chevron"
          onClick={(e) => { e.stopPropagation(); toggleCollapse(); }}
          aria-label={isCollapsed ? 'Expand panel' : 'Collapse panel'}
        >
          {isCollapsed ? '›' : '⌄'}
        </button>
      </div>
      {!isCollapsed && (
        <div className="panel-content">
          {children}
        </div>
      )}
    </div>
  );
}
