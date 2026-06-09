import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'
import ScheduleCalendar from './ScheduleCalendar.jsx'

test('renders day column headers Mon-Sun', () => {
  render(<ScheduleCalendar scheduleText="" />)
  expect(screen.getByText('Mon')).toBeInTheDocument()
  expect(screen.getByText('Fri')).toBeInTheDocument()
  expect(screen.getByText('Sun')).toBeInTheDocument()
})

test('shows empty message when no events', () => {
  render(<ScheduleCalendar scheduleText={null} />)
  expect(screen.getByText(/no events parsed yet/i)).toBeInTheDocument()
})

test('renders event blocks for parsed schedule', () => {
  const text = 'Mon 09:00-11:00 Calculus\nWed 14:00-16:00 Programming Lab'
  render(<ScheduleCalendar scheduleText={text} />)
  expect(screen.getByText('Calculus')).toBeInTheDocument()
  expect(screen.getByText('Programming Lab')).toBeInTheDocument()
})

test('has accessible aria-label', () => {
  render(<ScheduleCalendar scheduleText="" />)
  expect(screen.getByRole('generic', { name: /weekly schedule calendar/i })).toBeInTheDocument()
})
