import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import { FloatingPanel } from './FloatingPanel.jsx';

describe('FloatingPanel', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('renders title and children', () => {
    render(
      <FloatingPanel panelId="fp1" title="My Panel">
        <div>Child Content</div>
      </FloatingPanel>
    );
    expect(screen.getByText('My Panel')).toBeTruthy();
    expect(screen.getByText('Child Content')).toBeTruthy();
  });

  it('has frosted-glass class', () => {
    const { container } = render(
      <FloatingPanel panelId="fp2" title="Test">Content</FloatingPanel>
    );
    expect(container.querySelector('.floating-panel').className).toContain('frosted-glass');
  });

  it('uses fixed positioning with left/top style', () => {
    const { container } = render(
      <FloatingPanel panelId="fp3" title="Test" defaultPosition={{ x: 42, y: 77 }}>
        Content
      </FloatingPanel>
    );
    const panel = container.querySelector('.floating-panel');
    expect(panel.style.left).toBe('42px');
    expect(panel.style.top).toBe('77px');
  });

  it('renders a chevron button in the header', () => {
    render(
      <FloatingPanel panelId="fp4" title="Test">Content</FloatingPanel>
    );
    expect(screen.getByRole('button', { name: /collapse/i })).toBeTruthy();
  });

  it('collapses and hides content when chevron is clicked', () => {
    render(
      <FloatingPanel panelId="fp5" title="Test">
        <div>Hidden When Collapsed</div>
      </FloatingPanel>
    );
    expect(screen.getByText('Hidden When Collapsed')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: /collapse/i }));
    expect(screen.queryByText('Hidden When Collapsed')).toBeNull();
  });

  it('expands again when chevron is clicked a second time', () => {
    render(
      <FloatingPanel panelId="fp6" title="Test">
        <div>Toggle Content</div>
      </FloatingPanel>
    );
    const btn = screen.getByRole('button', { name: /collapse/i });
    fireEvent.click(btn);
    expect(screen.queryByText('Toggle Content')).toBeNull();
    fireEvent.click(btn);
    expect(screen.getByText('Toggle Content')).toBeTruthy();
  });
});
