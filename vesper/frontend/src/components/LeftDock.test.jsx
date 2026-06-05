import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, test, vi, beforeEach, afterEach } from 'vitest'
import LeftDock from './LeftDock.jsx'
import * as feedModule from '../hooks/useFeed.js'

// Default mock for useFeed so existing tests don't hit real network
vi.mock('../hooks/useFeed.js', () => ({
  useFeed: () => ({ items: [], unreadCount: 0, markRead: vi.fn(), loading: false, error: null }),
}))

function makeCap() {
  return {
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
  }
}

test('Memory is the default tab', () => {
  render(<LeftDock memoryResults={[]} onSearch={vi.fn()} cap={makeCap()} />)
  expect(screen.getByPlaceholderText(/search vault/i)).toBeInTheDocument()
})

test('switching to Finance shows the expense form', async () => {
  render(<LeftDock memoryResults={[]} onSearch={vi.fn()} cap={makeCap()} />)
  await userEvent.click(screen.getByRole('tab', { name: 'Finance' }))
  expect(screen.getByPlaceholderText(/amount/i)).toBeInTheDocument()
})

test('switching to Files shows the vault browser', async () => {
  render(<LeftDock memoryResults={[]} onSearch={vi.fn()} cap={makeCap()} />)
  await userEvent.click(screen.getByRole('tab', { name: 'Files' }))
  expect(await screen.findByText(/vault root/i)).toBeInTheDocument()
})

test('the Uploads tab is present', () => {
  render(<LeftDock memoryResults={[]} onSearch={vi.fn()} cap={makeCap()} />)
  expect(screen.getByRole('tab', { name: 'Uploads' })).toBeInTheDocument()
})

test('switching to Uploads shows the dropzone', async () => {
  render(<LeftDock memoryResults={[]} onSearch={vi.fn()} cap={makeCap()} />)
  await userEvent.click(screen.getByRole('tab', { name: 'Uploads' }))
  expect(await screen.findByText(/drop a \.pptx/i)).toBeInTheDocument()
})

describe('Alerts tab', () => {
  beforeEach(() => {
    vi.spyOn(feedModule, 'useFeed').mockReturnValue({
      items: [{ id: 'x', kind: 'error', title: 'Error in x', body: '', priority: 'urgent', read: false, created_at: '' }],
      unreadCount: 1,
      markRead: vi.fn(),
      loading: false,
      error: null,
    })
  })
  afterEach(() => vi.restoreAllMocks())

  test('renders the Alerts tab button', () => {
    render(<LeftDock memoryResults={[]} onSearch={vi.fn()} cap={makeCap()} />)
    expect(screen.getByRole('tab', { name: /Alerts/i })).toBeTruthy()
  })

  test('shows unread badge on Alerts tab when unreadCount > 0', () => {
    render(<LeftDock memoryResults={[]} onSearch={vi.fn()} cap={makeCap()} />)
    expect(screen.getByText('1')).toBeTruthy()
  })

  test('renders FeedPanel when Alerts tab is active', async () => {
    render(<LeftDock memoryResults={[]} onSearch={vi.fn()} cap={makeCap()} />)
    await userEvent.click(screen.getByRole('tab', { name: /Alerts/i }))
    expect(screen.getByText('Error in x')).toBeTruthy()
  })
})

test('Memory tab has the left-dock-tab class', () => {
  render(<LeftDock memoryResults={[]} onSearch={vi.fn()} cap={makeCap()} />)
  const memoryTab = screen.getByRole('tab', { name: 'Memory' })
  expect(memoryTab).toHaveClass('left-dock-tab')
})

test('renders resizer handle', () => {
  render(<LeftDock memoryResults={[]} onSearch={vi.fn()} cap={makeCap()} onResizeStart={vi.fn()} />)
  expect(document.querySelector('.left-dock-resizer')).toBeInTheDocument()
})
