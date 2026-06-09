import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'
import ScheduleTimeline from './ScheduleTimeline.jsx'

test('shows empty state when no schedule text provided', () => {
  render(<ScheduleTimeline scheduleText={null} />)
  expect(screen.getByText(/no events parsed yet/i)).toBeInTheDocument()
})

test('shows day labels and event titles for valid schedule', () => {
  const text = 'Mon 09:00-11:00 Calculus\nWed 14:00-16:00 Programming Lab'
  render(<ScheduleTimeline scheduleText={text} />)
  expect(screen.getByText('Monday')).toBeInTheDocument()
  expect(screen.getByText('Calculus')).toBeInTheDocument()
  expect(screen.getByText('Wednesday')).toBeInTheDocument()
  expect(screen.getByText('Programming Lab')).toBeInTheDocument()
})

test('shows event start times', () => {
  const text = 'Mon 09:00-11:00 Calculus'
  render(<ScheduleTimeline scheduleText={text} />)
  expect(screen.getByText('09:00')).toBeInTheDocument()
})

test('shows event duration', () => {
  const text = 'Mon 09:00-11:00 Calculus'
  render(<ScheduleTimeline scheduleText={text} />)
  expect(screen.getByText('2h')).toBeInTheDocument()
})

test('shows location when present', () => {
  const text = 'Mon 09:00-11:00 Calculus (Room 101)'
  render(<ScheduleTimeline scheduleText={text} />)
  expect(screen.getByText('Room 101')).toBeInTheDocument()
})

test('sorts events within the same day by start time', () => {
  const text = 'Mon 14:00-16:00 Lab\nMon 09:00-11:00 Calculus'
  render(<ScheduleTimeline scheduleText={text} />)
  const titles = screen.getAllByText(/Calculus|Lab/)
  expect(titles[0].textContent).toBe('Calculus')
  expect(titles[1].textContent).toBe('Lab')
})
