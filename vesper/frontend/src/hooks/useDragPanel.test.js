import { renderHook, act } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { useDragPanel } from './useDragPanel.js';

describe('useDragPanel', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('uses default position object when localStorage is empty', () => {
    const { result } = renderHook(() => useDragPanel('p1', { x: 10, y: 20 }));
    expect(result.current.position).toEqual({ x: 10, y: 20 });
  });

  it('uses default position function when localStorage is empty', () => {
    const { result } = renderHook(() => useDragPanel('p2', () => ({ x: 50, y: 60 })));
    expect(result.current.position).toEqual({ x: 50, y: 60 });
  });

  it('restores position from localStorage on mount', () => {
    localStorage.setItem('panel-p3-pos', JSON.stringify({ x: 100, y: 200 }));
    const { result } = renderHook(() => useDragPanel('p3'));
    expect(result.current.position).toEqual({ x: 100, y: 200 });
  });

  it('starts with isCollapsed false when localStorage is empty', () => {
    const { result } = renderHook(() => useDragPanel('p4', { x: 0, y: 0 }));
    expect(result.current.isCollapsed).toBe(false);
  });

  it('restores collapsed state from localStorage', () => {
    localStorage.setItem('panel-p5-collapsed', 'true');
    const { result } = renderHook(() => useDragPanel('p5', { x: 0, y: 0 }));
    expect(result.current.isCollapsed).toBe(true);
  });

  it('toggleCollapse flips isCollapsed and persists to localStorage', () => {
    const { result } = renderHook(() => useDragPanel('p6', { x: 0, y: 0 }));
    act(() => result.current.toggleCollapse());
    expect(result.current.isCollapsed).toBe(true);
    expect(localStorage.getItem('panel-p6-collapsed')).toBe('true');
    act(() => result.current.toggleCollapse());
    expect(result.current.isCollapsed).toBe(false);
    expect(localStorage.getItem('panel-p6-collapsed')).toBe('false');
  });

  it('startDrag attaches mousemove and mouseup listeners to document', () => {
    const addSpy = vi.spyOn(document, 'addEventListener');
    const { result } = renderHook(() => useDragPanel('p7', { x: 0, y: 0 }));
    act(() => {
      result.current.startDrag({ clientX: 10, clientY: 10, preventDefault: vi.fn() });
    });
    expect(addSpy).toHaveBeenCalledWith('mousemove', expect.any(Function));
    expect(addSpy).toHaveBeenCalledWith('mouseup', expect.any(Function));
    addSpy.mockRestore();
  });

  it('mouseup removes document listeners and saves position to localStorage', () => {
    const removeSpy = vi.spyOn(document, 'removeEventListener');
    const { result } = renderHook(() => useDragPanel('p8', { x: 0, y: 0 }));

    act(() => {
      result.current.startDrag({ clientX: 0, clientY: 0, preventDefault: vi.fn() });
    });

    act(() => {
      document.dispatchEvent(new MouseEvent('mousemove', { clientX: 80, clientY: 90, bubbles: true }));
    });

    act(() => {
      document.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
    });

    expect(removeSpy).toHaveBeenCalledWith('mousemove', expect.any(Function));
    expect(removeSpy).toHaveBeenCalledWith('mouseup', expect.any(Function));
    const saved = JSON.parse(localStorage.getItem('panel-p8-pos'));
    expect(saved).toEqual({ x: 80, y: 90 });
    removeSpy.mockRestore();
  });
});
