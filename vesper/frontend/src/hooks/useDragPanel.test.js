import { renderHook, act } from '@testing-library/react';
import { useDragPanel } from './useDragPanel.js';

describe('useDragPanel', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('should initialize position from localStorage if available', () => {
    localStorage.setItem('panel-test-pos', JSON.stringify({ x: 100, y: 200 }));
    const { result } = renderHook(() => useDragPanel('test'));
    expect(result.current.position).toEqual({ x: 100, y: 200 });
  });

  it('should use default position if localStorage is empty', () => {
    const { result } = renderHook(() => useDragPanel('test', { x: 10, y: 10 }));
    expect(result.current.position).toEqual({ x: 10, y: 10 });
  });

  it('should update position on drag and save to localStorage', () => {
    const { result } = renderHook(() => useDragPanel('test', { x: 0, y: 0 }));

    act(() => {
      result.current.startDrag({ clientX: 50, clientY: 50 });
      result.current.onDrag({ clientX: 150, clientY: 200 });
    });

    expect(result.current.position).toEqual({ x: 100, y: 150 });
    expect(JSON.parse(localStorage.getItem('panel-test-pos'))).toEqual({ x: 100, y: 150 });
  });

  it('should stop dragging on stopDrag', () => {
    const { result } = renderHook(() => useDragPanel('test'));

    act(() => {
      result.current.startDrag({ clientX: 0, clientY: 0 });
    });
    expect(result.current.isDragging).toBe(true);

    act(() => {
      result.current.stopDrag();
    });
    expect(result.current.isDragging).toBe(false);
  });
});
