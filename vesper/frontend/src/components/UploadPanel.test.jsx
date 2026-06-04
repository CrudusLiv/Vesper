import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, test, vi } from 'vitest'
import UploadPanel from './UploadPanel.jsx'

test('lists uploads on mount: a done row links to the note, a failed row shows retry copy', async () => {
  const onListUploads = vi.fn().mockResolvedValue([
    { id: '1', filename: 'CS101.pptx', status: 'done', type: 'lecture', category: 'CS101', title: 'Sorting', note_path: 'lectures/CS101/x.md', error: null },
    { id: '2', filename: 'broken.pdf', status: 'failed', type: null, category: null, title: null, note_path: null, error: 'no text' },
  ])
  render(<UploadPanel onUpload={vi.fn()} onListUploads={onListUploads} />)
  const link = await screen.findByRole('link', { name: /Sorting/ })
  expect(link).toHaveAttribute('href', 'obsidian://open?vault=Memory&file=lectures%2FCS101%2Fx.md')
  expect(screen.getByText(/will retry/i)).toBeInTheDocument()
})

test('shows a processing row with a pending indicator', async () => {
  const onListUploads = vi.fn().mockResolvedValue([
    { id: '3', filename: 'wip.pptx', status: 'processing', type: null, category: null, title: null, note_path: null, error: null },
  ])
  render(<UploadPanel onUpload={vi.fn()} onListUploads={onListUploads} />)
  expect(await screen.findByText(/wip\.pptx/)).toBeInTheDocument()
  expect(screen.getByText(/processing/i)).toBeInTheDocument()
})

test('choosing a file calls onUpload with the file then refreshes the list', async () => {
  const onUpload = vi.fn().mockResolvedValue({ id: '9', filename: 'New.pptx', status: 'queued' })
  const onListUploads = vi.fn().mockResolvedValue([])
  render(<UploadPanel onUpload={onUpload} onListUploads={onListUploads} />)
  const file = new File(['data'], 'New.pptx', { type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation' })
  await userEvent.upload(screen.getByTestId('upload-input'), file)
  expect(onUpload).toHaveBeenCalledWith(file)
  // one call on mount + one after the upload
  expect(onListUploads.mock.calls.length).toBeGreaterThanOrEqual(2)
})
