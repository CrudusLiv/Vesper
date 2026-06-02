import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, test, vi } from 'vitest'
import MemoryPanel from './MemoryPanel.jsx'

const results = [
  { path: 'projects/DIP209/note.md', heading: 'Intro', score: 0.83 },
]

test('renders results with score and an Obsidian deep-link', () => {
  render(<MemoryPanel results={results} onSearch={() => {}} />)
  expect(screen.getByText('projects/DIP209/note.md')).toBeInTheDocument()
  expect(screen.getByText(/0\.83/)).toBeInTheDocument()
  const link = screen.getByRole('link')
  expect(link).toHaveAttribute(
    'href',
    'obsidian://open?vault=Memory&file=projects%2FDIP209%2Fnote.md',
  )
})

test('typing in the search box calls onSearch with the query', async () => {
  const onSearch = vi.fn()
  render(<MemoryPanel results={[]} onSearch={onSearch} />)
  await userEvent.type(screen.getByPlaceholderText(/search vault/i), 'deadline')
  expect(onSearch).toHaveBeenLastCalledWith('deadline')
})
