import { render, screen } from '@testing-library/react';
import { ParticleOrb } from './ParticleOrb.jsx';

describe('ParticleOrb', () => {
  it('should render a canvas element', () => {
    render(<ParticleOrb state="idle" />);
    const canvas = screen.getByTestId('orb-idle');
    expect(canvas).toBeTruthy();
    expect(canvas.tagName).toBe('CANVAS');
  });

  it('should accept idle, listening, speaking, and processing states', () => {
    const states = ['idle', 'listening', 'speaking', 'processing'];
    states.forEach(state => {
      const { rerender } = render(<ParticleOrb state={state} />);
      expect(screen.getByTestId(`orb-${state}`)).toBeTruthy();
      rerender(<ParticleOrb state={state} />);
    });
  });

  it('should update animation when state changes', () => {
    const { rerender } = render(<ParticleOrb state="idle" />);
    const canvas = screen.getByTestId('orb-idle');
    expect(canvas).toBeTruthy();

    rerender(<ParticleOrb state="listening" />);
    expect(screen.getByTestId('orb-listening')).toBeTruthy();
    expect(canvas.getAttribute('data-testid')).toBe('orb-listening');
  });
});
