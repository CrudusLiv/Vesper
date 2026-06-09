import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, test, vi } from 'vitest'
import SchedulePanel from './SchedulePanel.jsx'
import { ConflictError } from '../api/client.js'

async function openEditTab() {
  await userEvent.click(screen.getByRole('button', { name: /edit/i }))
}

test('shows the current schedule in the edit view', async () => {
  const onLoad = vi.fn().mockResolvedValue({ schedule: 'Mon 9-10 Maths' })
  render(<SchedulePanel onLoad={onLoad} onSave={vi.fn()} />)
  await openEditTab()
  expect(await screen.findByText(/Mon 9-10 Maths/)).toBeInTheDocument()
})

test('defaults to timeline view with view toggle buttons', () => {
  render(<SchedulePanel onLoad={vi.fn().mockResolvedValue(null)} onSave={vi.fn()} />)
  expect(screen.getByRole('button', { name: /timeline/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /calendar/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /edit/i })).toBeInTheDocument()
})

test('a 409 shows the replace dialog, then confirming re-saves with confirm=true', async () => {
  const onLoad = vi.fn().mockResolvedValue({ schedule: 'Mon 9-10 Maths' })
  const onSave = vi.fn()
    .mockRejectedValueOnce(new ConflictError({ summary: 'parsed preview', exists: true }))
    .mockResolvedValueOnce({ summary: 'ok' })
  render(<SchedulePanel onLoad={onLoad} onSave={onSave} />)
  await openEditTab()
  await userEvent.type(screen.getByPlaceholderText(/timetable/i), 'tue 10-11 cs')
  await userEvent.click(screen.getByRole('button', { name: /set schedule/i }))
  expect(await screen.findByText(/parsed preview/)).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: /^replace$/i }))
  expect(onSave).toHaveBeenLastCalledWith('tue 10-11 cs', true)
})

test('a non-conflict error shows a parse-error status, not the replace dialog', async () => {
  const onLoad = vi.fn().mockResolvedValue({ schedule: null })
  const onSave = vi.fn().mockRejectedValue(new Error('boom'))
  render(<SchedulePanel onLoad={onLoad} onSave={onSave} />)
  await openEditTab()
  await userEvent.type(screen.getByPlaceholderText(/timetable/i), 'tue 10-11 cs')
  await userEvent.click(screen.getByRole('button', { name: /set schedule/i }))
  expect(await screen.findByText(/could not parse/i)).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /^replace$/i })).not.toBeInTheDocument()
})
