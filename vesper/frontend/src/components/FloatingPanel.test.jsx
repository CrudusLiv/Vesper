import { render, screen, fireEvent } from '@testing-library/react';
import { FloatingPanel } from './FloatingPanel.jsx';

describe('FloatingPanel', () => {
  it('should render with title and children', () => {
    render(
      <FloatingPanel panelId="test" title="Test Panel">
        <div>Test Content</div>
      </FloatingPanel>
    );
    expect(screen.getByText('Test Panel')).toBeTruthy();
    expect(screen.getByText('Test Content')).toBeTruthy();
  });

  it('should apply frosted glass styling', () => {
    const { container } = render(
      <FloatingPanel panelId="test" title="Test">
        Content
      </FloatingPanel>
    );
    const panel = container.querySelector('.floating-panel');
    expect(panel.className).toContain('frosted-glass');
  });

  it('should be draggable by header', () => {
    const { container } = render(
      <FloatingPanel panelId="test" title="Test" defaultPosition={{ x: 0, y: 0 }}>
        Content
      </FloatingPanel>
    );
    const header = screen.getByText('Test').closest('.panel-header');

    fireEvent.mouseDown(header);
    fireEvent.mouseMove(window, { clientX: 100, clientY: 100 });
    fireEvent.mouseUp(window);

    const panel = container.querySelector('.floating-panel');
    expect(panel.style.transform).toContain('translate');
  });
});
