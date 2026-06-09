import { render, screen, fireEvent } from '@testing-library/react'
import { expect, test, describe, vi } from 'vitest'
import { ActivePanel } from './ActivePanel.jsx'

vi.mock('../hooks/useAgent.js', () => ({
  useAgent: () => ({
    messages: [],
    pending: false,
    toolCalls: [],
    toolResults: [],
    send: vi.fn(),
  }),
}))

vi.mock('../hooks/useVoice.js', () => ({
  useVoice: () => ({
    listening: false,
    speaking: false,
    sttSupported: true,
    ttsSupported: false,
    startListening: vi.fn(),
    stopListening: vi.fn(),
    speak: vi.fn(),
    cancelSpeech: vi.fn(),
  }),
}))

describe('ActivePanel', () => {
  const mockProps = {
    memoryResults: [],
    onSearch: vi.fn(),
  }

  test('renders Chat tab by default with message input', () => {
    render(<ActivePanel {...mockProps} />)
    expect(screen.getByPlaceholderText(/message vesper/i)).toBeTruthy()
  })

  test('switching to Search tab shows search input', () => {
    render(<ActivePanel {...mockProps} />)
    fireEvent.click(screen.getByRole('tab', { name: 'Search' }))
    expect(screen.getByPlaceholderText(/search vault/i)).toBeTruthy()
  })

  test('switching back to Chat shows message input again', () => {
    render(<ActivePanel {...mockProps} />)
    fireEvent.click(screen.getByRole('tab', { name: 'Search' }))
    fireEvent.click(screen.getByRole('tab', { name: 'Chat' }))
    expect(screen.getByPlaceholderText(/message vesper/i)).toBeTruthy()
  })
})
