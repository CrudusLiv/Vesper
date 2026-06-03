import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, test, vi } from 'vitest'
import SchedulePanel from './SchedulePanel.jsx'
import { ConflictError } from '../api/client.js'

test('shows the current schedule loaded on mount', async () => {
  const onLoad = vi.fn().mockResolvedValue({ schedule: 'Mon 9-10 Maths' })
  render(<SchedulePanel onLoad={onLoad} onSave={vi.fn()} />)
  expect(await screen.findByText(/Mon 9-10 Maths/)).toBeInTheDocument()
})

test('a 409 shows the replace dialog, then confirming re-saves with confirm=true', async () => {
  const onLoad = vi.fn().mockResolvedValue({ schedule: 'Mon 9-10 Maths' })
  const onSave = vi.fn()
    .mockRejectedValueOnce(new ConflictError({ summary: 'parsed preview', exists: true }))
    .mockResolvedValueOnce({ summary: 'ok' })
  render(<SchedulePanel onLoad={onLoad} onSave={onSave} />)
  await userEvent.type(screen.getByPlaceholderText(/timetable/i), 'tue 10-11 cs')
  await userEvent.click(screen.getByRole('button', { name: /set schedule/i }))
  expect(await screen.findByText(/parsed preview/)).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: /^replace$/i }))
  expect(onSave).toHaveBeenLastCalledWith('tue 10-11 cs', true)
})
