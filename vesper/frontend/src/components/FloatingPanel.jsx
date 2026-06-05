import { useDragPanel } from '../hooks/useDragPanel.js';
import './FloatingPanel.css';

export function FloatingPanel({ panelId, title, children, defaultPosition = { x: 20, y: 20 } }) {
  const { position, isDragging, startDrag, onDrag, stopDrag } = useDragPanel(panelId, defaultPosition);

  // Attach event listeners when dragging
  const handleMouseDown = (e) => {
    startDrag(e);
  };

  const handleMouseMove = (e) => {
    if (isDragging) {
      onDrag(e);
    }
  };

  const handleMouseUp = () => {
    stopDrag();
  };

  return (
    <>
      <div
        className="floating-panel frosted-glass"
        style={{
          transform: `translate(${position.x}px, ${position.y}px)`,
          cursor: isDragging ? 'grabbing' : 'grab',
        }}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <div
          className="panel-header"
          onMouseDown={handleMouseDown}
        >
          <h3 className="panel-title">{title}</h3>
        </div>
        <div className="panel-content">
          {children}
        </div>
      </div>
    </>
  );
}
