import { useState, useRef, useCallback, useEffect } from 'react';

export function useDragPanel(panelId, defaultPosition = { x: 20, y: 20 }) {
  const resolveDefault = () =>
    typeof defaultPosition === 'function' ? defaultPosition() : defaultPosition;

  const [position, setPosition] = useState(() => {
    const saved = localStorage.getItem(`panel-${panelId}-pos`);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        return {
          x: Math.max(0, parsed.x ?? 20),
          y: Math.max(0, parsed.y ?? 20),
        };
      } catch { /* ignore bad data */ }
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

  // Refs to hold the active drag listeners so they can be cleaned up on unmount
  const activeMoveRef = useRef(null);
  const activeUpRef = useRef(null);

  // Cleanup drag listeners if the component unmounts mid-drag
  useEffect(() => {
    return () => {
      if (activeMoveRef.current) {
        document.removeEventListener('mousemove', activeMoveRef.current);
        activeMoveRef.current = null;
      }
      if (activeUpRef.current) {
        document.removeEventListener('mouseup', activeUpRef.current);
        activeUpRef.current = null;
      }
    };
  }, []);

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
        x: Math.max(0, moveEvent.clientX - dragOffsetRef.current.x),
        y: Math.max(0, moveEvent.clientY - dragOffsetRef.current.y),
      };
      positionRef.current = newPos;
      setPosition(newPos);
    };

    const onUp = () => {
      setIsDragging(false);
      localStorage.setItem(`panel-${panelId}-pos`, JSON.stringify(positionRef.current));
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      activeMoveRef.current = null;
      activeUpRef.current = null;
    };

    activeMoveRef.current = onMove;
    activeUpRef.current = onUp;

    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }, [panelId]);

  return { position, isDragging, isCollapsed, startDrag, toggleCollapse };
}
