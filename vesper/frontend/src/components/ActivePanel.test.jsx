import { render, screen, fireEvent } from '@testing-library/react';
import { expect, test, describe, vi } from 'vitest';
import { ActivePanel } from './ActivePanel.jsx';

describe('ActivePanel', () => {
  const mockProps = {
    memoryResults: [],
    onSearch: vi.fn(),
    messages: [],
    pending: false,
    onSend: vi.fn(),
    voiceSupported: true,
    listening: false,
    onMic: vi.fn(),
  };

  test('should render search tab by default', () => {
    render(<ActivePanel {...mockProps} />);
    expect(screen.getByText('Search')).toBeTruthy();
  });

  test('should switch to chat when Chat tab is clicked', () => {
    render(<ActivePanel {...mockProps} />);
    fireEvent.click(screen.getByText('Chat'));
    expect(screen.getByPlaceholderText(/message vesper/i)).toBeTruthy();
  });

  test('should switch back to search when Search tab is clicked', () => {
    render(<ActivePanel {...mockProps} />);
    fireEvent.click(screen.getByText('Chat'));
    fireEvent.click(screen.getByText('Search'));
    expect(screen.getByPlaceholderText(/search vault/i)).toBeTruthy();
  });
});
