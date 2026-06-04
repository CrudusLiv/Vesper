import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, test, vi } from 'vitest'
import VaultBrowser from './VaultBrowser.jsx'

test('lists root entries: folders as buttons, files as Obsidian links', async () => {
  const onList = vi.fn().mockResolvedValue({ directory: '', entries: [
    { name: 'notes', is_dir: true }, { name: 'todo.md', is_dir: false },
  ] })
  render(<VaultBrowser onList={onList} onDelete={vi.fn()} onUndo={vi.fn()} />)
  expect(await screen.findByRole('button', { name: 'notes' })).toBeInTheDocument()
  const link = screen.getByRole('link', { name: /todo\.md/ })
  expect(link).toHaveAttribute('href', 'obsidian://open?vault=Memory&file=todo.md')
})

test('clicking a folder lists its children', async () => {
  const onList = vi.fn()
    .mockResolvedValueOnce({ directory: '', entries: [{ name: 'notes', is_dir: true }] })
    .mockResolvedValueOnce({ directory: 'notes', entries: [{ name: 'x.md', is_dir: false }] })
  render(<VaultBrowser onList={onList} onDelete={vi.fn()} onUndo={vi.fn()} />)
  await userEvent.click(await screen.findByRole('button', { name: 'notes' }))
  expect(await screen.findByRole('link', { name: /x\.md/ })).toBeInTheDocument()
  expect(onList).toHaveBeenLastCalledWith('notes')
})

test('deleting a file calls onDelete with the full path', async () => {
  const onList = vi.fn().mockResolvedValue({ directory: 'notes', entries: [{ name: 'x.md', is_dir: false }] })
  const onDelete = vi.fn().mockResolvedValue({ path: 'notes/x.md', trash_path: '_trash/x.md' })
  render(<VaultBrowser onList={onList} onDelete={onDelete} onUndo={vi.fn()} />)
  await userEvent.click(await screen.findByRole('button', { name: /delete x\.md/i }))
  expect(onDelete).toHaveBeenCalledWith('notes/x.md')
})

test('undo calls onUndo and shows the returned message', async () => {
  const onList = vi.fn().mockResolvedValue({ directory: '', entries: [] })
  const onUndo = vi.fn().mockResolvedValue({ message: 'restored notes/x.md from trash' })
  render(<VaultBrowser onList={onList} onDelete={vi.fn()} onUndo={onUndo} />)
  await userEvent.click(await screen.findByRole('button', { name: /undo/i }))
  expect(await screen.findByText(/restored/i)).toBeInTheDocument()
})
