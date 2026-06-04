import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, test, vi } from 'vitest'
import NotesPanel from './NotesPanel.jsx'

test('saving sends the note text and shows a confirmation', async () => {
  const onSave = vi.fn().mockResolvedValue({ ok: true, appended_chars: 8 })
  render(<NotesPanel onSave={onSave} />)
  await userEvent.type(screen.getByPlaceholderText(/note/i), 'buy milk')
  await userEvent.click(screen.getByRole('button', { name: /save note/i }))
  expect(onSave).toHaveBeenCalledWith('buy milk')
  expect(await screen.findByText(/saved/i)).toBeInTheDocument()
})

test('the save button is disabled when the note is empty', () => {
  render(<NotesPanel onSave={vi.fn()} />)
  expect(screen.getByRole('button', { name: /save note/i })).toBeDisabled()
})
