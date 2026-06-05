import { useState, useEffect, useRef } from 'react';

export function useDragPanel(panelId, defaultPosition = { x: 20, y: 20 }) {
  const [position, setPosition] = useState(defaultPosition);
  const [isDragging, setIsDragging] = useState(false);
  const dragOffsetRef = useRef({ x: 0, y: 0 });

  // Load position from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem(`panel-${panelId}-pos`);
    if (saved) {
      try {
        setPosition(JSON.parse(saved));
      } catch (e) {
        console.error(`Failed to load panel position for ${panelId}:`, e);
      }
    }
  }, [panelId]);

  const startDrag = (e) => {
    dragOffsetRef.current = {
      x: e.clientX - position.x,
      y: e.clientY - position.y,
    };
    setIsDragging(true);
  };

  const onDrag = (e) => {
    const newPos = {
      x: e.clientX - dragOffsetRef.current.x,
      y: e.clientY - dragOffsetRef.current.y,
    };
    setPosition(newPos);
  };

  const stopDrag = () => {
    setIsDragging(false);
  };

  // Save position to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem(`panel-${panelId}-pos`, JSON.stringify(position));
  }, [position, panelId]);

  return {
    position,
    isDragging,
    startDrag,
    onDrag,
    stopDrag,
  };
}
