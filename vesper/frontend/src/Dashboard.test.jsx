import { render, fireEvent } from '@testing-library/react'
import { describe, test, expect, vi, beforeEach } from 'vitest'
import Dashboard from './Dashboard.jsx'

vi.mock('./state/store.jsx', () => ({
  useStore: () => ({
    state: {
      memory: { results: [] },
      chat: { messages: [], pending: false },
      status: null,
      orb: 'idle',
    },
  }),
}))

vi.mock('./hooks/useVesper.js', () => ({
  useVesper: () => ({
    sendChat: vi.fn(),
    search: vi.fn(),
    startVoice: vi.fn(),
    stopVoice: vi.fn(),
    sttSupported: false,
  }),
}))

vi.mock('./hooks/useCapture.js', () => ({
  useCapture: () => ({
    logFinance: vi.fn(),
    loadFinanceSummary: vi.fn().mockResolvedValue({ summary: '' }),
    saveNote: vi.fn(),
    getSchedule: vi.fn().mockResolvedValue({ schedule: null }),
    saveSchedule: vi.fn(),
    listVault: vi.fn().mockResolvedValue({ directory: '', entries: [] }),
    deleteVaultFile: vi.fn(),
    undoVault: vi.fn(),
    uploadDocument: vi.fn(),
    listUploads: vi.fn().mockResolvedValue([]),
  }),
}))

vi.mock('./hooks/useFeed.js', () => ({
  useFeed: () => ({ items: [], unreadCount: 0, markRead: vi.fn(), loading: false, error: null }),
}))

beforeEach(() => {
  localStorage.clear()
})

test('sidebar defaults to 220px when localStorage is empty', () => {
  render(<Dashboard />)
  const sidebar = document.querySelector('.dashboard-sidebar')
  expect(sidebar.style.width).toBe('220px')
})

test('sidebar loads persisted width from localStorage', () => {
  localStorage.setItem('left-dock-width', '300')
  render(<Dashboard />)
  const sidebar = document.querySelector('.dashboard-sidebar')
  expect(sidebar.style.width).toBe('300px')
})

test('dragging resizer updates sidebar width', () => {
  render(<Dashboard />)
  const resizer = document.querySelector('.left-dock-resizer')
  fireEvent.mouseDown(resizer)
  fireEvent.mouseMove(document, { clientX: 280 })
  const sidebar = document.querySelector('.dashboard-sidebar')
  expect(sidebar.style.width).toBe('280px')
})

test('sidebar width is clamped to minimum 160px', () => {
  render(<Dashboard />)
  const resizer = document.querySelector('.left-dock-resizer')
  fireEvent.mouseDown(resizer)
  fireEvent.mouseMove(document, { clientX: 50 })
  const sidebar = document.querySelector('.dashboard-sidebar')
  expect(sidebar.style.width).toBe('160px')
})

test('sidebar width is clamped to maximum 400px', () => {
  render(<Dashboard />)
  const resizer = document.querySelector('.left-dock-resizer')
  fireEvent.mouseDown(resizer)
  fireEvent.mouseMove(document, { clientX: 600 })
  const sidebar = document.querySelector('.dashboard-sidebar')
  expect(sidebar.style.width).toBe('400px')
})

test('mouseup saves final width to localStorage', () => {
  render(<Dashboard />)
  const resizer = document.querySelector('.left-dock-resizer')
  fireEvent.mouseDown(resizer)
  fireEvent.mouseMove(document, { clientX: 280 })
  fireEvent.mouseUp(document)
  expect(localStorage.getItem('left-dock-width')).toBe('280')
})
