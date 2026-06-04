import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, test, vi } from 'vitest'
import ChatPanel from './ChatPanel.jsx'

const messages = [
  { role: 'user', content: 'hi', ts: 1 },
  { role: 'assistant', content: 'hello', sources: [{ path: 'a' }, { path: 'b' }], ts: 2 },
]

test('renders messages and a source count for assistant replies', () => {
  render(<ChatPanel messages={messages} pending={false} onSend={() => {}} />)
  expect(screen.getByText('hi')).toBeInTheDocument()
  expect(screen.getByText('hello')).toBeInTheDocument()
  expect(screen.getByText(/2 sources/i)).toBeInTheDocument()
})

test('submitting the input calls onSend with the text and clears it', async () => {
  const onSend = vi.fn()
  render(<ChatPanel messages={[]} pending={false} onSend={onSend} />)
  const box = screen.getByPlaceholderText(/message vesper/i)
  await userEvent.type(box, 'what is up{enter}')
  expect(onSend).toHaveBeenCalledWith('what is up')
  expect(box).toHaveValue('')
})

test('does not send empty messages', async () => {
  const onSend = vi.fn()
  render(<ChatPanel messages={[]} pending={false} onSend={onSend} />)
  await userEvent.type(screen.getByPlaceholderText(/message vesper/i), '   {enter}')
  expect(onSend).not.toHaveBeenCalled()
})

test('mic button is disabled when voice is unsupported', () => {
  render(<ChatPanel messages={[]} pending={false} onSend={() => {}} voiceSupported={false} />)
  expect(screen.getByRole('button', { name: /voice/i })).toBeDisabled()
})

test('mic button calls onMic when supported and clicked', async () => {
  const onMic = vi.fn()
  render(<ChatPanel messages={[]} pending={false} onSend={() => {}} voiceSupported onMic={onMic} />)
  await userEvent.click(screen.getByRole('button', { name: /voice/i }))
  expect(onMic).toHaveBeenCalled()
})

test('mic button reflects listening via aria-pressed', () => {
  render(<ChatPanel messages={[]} pending={false} onSend={() => {}} voiceSupported listening onMic={() => {}} />)
  expect(screen.getByRole('button', { name: /voice/i })).toHaveAttribute('aria-pressed', 'true')
})
