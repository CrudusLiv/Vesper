import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, test, vi } from 'vitest'
import CommandCenter from './CommandCenter.jsx'

const mockSend = vi.fn()

vi.mock('../hooks/useAgent.js', () => ({
  useAgent: () => ({
    messages: [],
    pending: false,
    toolCalls: [],
    toolResults: [],
    send: mockSend,
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

test('renders the message input', () => {
  render(<CommandCenter />)
  expect(screen.getByPlaceholderText(/message vesper/i)).toBeInTheDocument()
})

test('shows empty state when no messages', () => {
  render(<CommandCenter />)
  expect(screen.getByText(/ask vesper anything/i)).toBeInTheDocument()
})

test('submitting the input calls send and clears the field', async () => {
  render(<CommandCenter />)
  const input = screen.getByPlaceholderText(/message vesper/i)
  await userEvent.type(input, 'hello{enter}')
  expect(mockSend).toHaveBeenCalledWith('hello')
  expect(input).toHaveValue('')
})

test('send button is disabled when input is empty', () => {
  render(<CommandCenter />)
  expect(screen.getByRole('button', { name: /send/i })).toBeDisabled()
})

test('mic button is present and enabled when voice is supported', () => {
  render(<CommandCenter />)
  expect(screen.getByRole('button', { name: /voice input/i })).not.toBeDisabled()
})

test('renders the tool palette', () => {
  render(<CommandCenter />)
  expect(screen.getByRole('toolbar')).toBeInTheDocument()
})

test('clicking a tool button prefills the input', async () => {
  render(<CommandCenter />)
  await userEvent.click(screen.getByRole('button', { name: /note/i }))
  expect(screen.getByPlaceholderText(/message vesper/i)).toHaveValue('Add a note: ')
})
