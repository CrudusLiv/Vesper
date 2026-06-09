import { expect, test } from 'vitest'
import { parseSchedule, timeToMinutes, getDayName, getDayShort } from './scheduleParser.js'

test('parseSchedule returns empty array for null/empty input', () => {
  expect(parseSchedule(null)).toEqual([])
  expect(parseSchedule('')).toEqual([])
})

test('parseSchedule handles inline day+time format', () => {
  const text = 'Mon 09:00-11:00 Calculus\nTue 14:00-16:00 Lab'
  const events = parseSchedule(text)
  expect(events).toHaveLength(2)
  expect(events[0]).toMatchObject({ day: 0, startTime: '09:00', endTime: '11:00', title: 'Calculus' })
  expect(events[1]).toMatchObject({ day: 1, startTime: '14:00', endTime: '16:00', title: 'Lab' })
})

test('parseSchedule handles day-header format', () => {
  const text = 'Monday\n09:00-11:00 Calculus\n14:00-16:00 Lab\nTuesday\n10:00-12:00 Data Structures'
  const events = parseSchedule(text)
  expect(events).toHaveLength(3)
  expect(events[0]).toMatchObject({ day: 0, title: 'Calculus' })
  expect(events[1]).toMatchObject({ day: 0, title: 'Lab' })
  expect(events[2]).toMatchObject({ day: 1, title: 'Data Structures' })
})

test('parseSchedule extracts location from parentheses', () => {
  const text = 'Mon 09:00-11:00 Calculus (Room 101)'
  const events = parseSchedule(text)
  expect(events[0].title).toBe('Calculus')
  expect(events[0].location).toBe('Room 101')
})

test('parseSchedule handles full day names inline', () => {
  const text = 'Wednesday 13:00-15:00 Programming Lab'
  const events = parseSchedule(text)
  expect(events[0]).toMatchObject({ day: 2, title: 'Programming Lab' })
})

test('timeToMinutes converts correctly', () => {
  expect(timeToMinutes('09:00')).toBe(540)
  expect(timeToMinutes('14:30')).toBe(870)
  expect(timeToMinutes('00:00')).toBe(0)
})

test('getDayName returns correct names', () => {
  expect(getDayName(0)).toBe('Monday')
  expect(getDayName(4)).toBe('Friday')
  expect(getDayName(6)).toBe('Sunday')
})

test('getDayShort returns correct abbreviations', () => {
  expect(getDayShort(0)).toBe('Mon')
  expect(getDayShort(2)).toBe('Wed')
})
