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
