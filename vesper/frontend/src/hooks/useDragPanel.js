import { useState, useRef, useCallback } from 'react';

export function useDragPanel(panelId, defaultPosition = { x: 20, y: 20 }) {
  const resolveDefault = () =>
    typeof defaultPosition === 'function' ? defaultPosition() : defaultPosition;

  const [position, setPosition] = useState(() => {
    const saved = localStorage.getItem(`panel-${panelId}-pos`);
    if (saved) {
      try { return JSON.parse(saved); } catch { /* ignore bad data */ }
    }
    return resolveDefault();
  });

  const [isDragging, setIsDragging] = useState(false);

  const [isCollapsed, setIsCollapsed] = useState(() => {
    return localStorage.getItem(`panel-${panelId}-collapsed`) === 'true';
  });

  const positionRef = useRef(position);
  positionRef.current = position;

  const dragOffsetRef = useRef({ x: 0, y: 0 });

  const toggleCollapse = useCallback(() => {
    setIsCollapsed(prev => {
      const next = !prev;
      localStorage.setItem(`panel-${panelId}-collapsed`, String(next));
      return next;
    });
  }, [panelId]);

  const startDrag = useCallback((e) => {
    e.preventDefault();
    dragOffsetRef.current = {
      x: e.clientX - positionRef.current.x,
      y: e.clientY - positionRef.current.y,
    };
    setIsDragging(true);

    const onMove = (moveEvent) => {
      const newPos = {
        x: moveEvent.clientX - dragOffsetRef.current.x,
        y: moveEvent.clientY - dragOffsetRef.current.y,
      };
      positionRef.current = newPos;
      setPosition(newPos);
    };

    const onUp = () => {
      setIsDragging(false);
      localStorage.setItem(`panel-${panelId}-pos`, JSON.stringify(positionRef.current));
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };

    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }, [panelId]);

  return { position, isDragging, isCollapsed, startDrag, toggleCollapse };
}
