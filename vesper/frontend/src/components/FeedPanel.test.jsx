import { render, screen, fireEvent } from '@testing-library/react'
import { vi, describe, it, expect } from 'vitest'
import FeedPanel from './FeedPanel.jsx'

const UNREAD = { id: 'u1', kind: 'deadline_24h', title: '[CS101] Lab', body: 'due tomorrow', priority: 'high', read: false, created_at: '2026-06-04T09:00:00+08:00' }
const READ   = { id: 'r1', kind: 'morning_digest', title: 'Morning', body: 'hello', priority: 'low', read: true, created_at: '2026-06-04T07:00:00+08:00' }

describe('FeedPanel', () => {
  it('shows empty state when items is empty', () => {
    render(<FeedPanel items={[]} markRead={vi.fn()} />)
    expect(screen.getByText(/No alerts yet/i)).toBeTruthy()
  })

  it('renders unread item title', () => {
    render(<FeedPanel items={[UNREAD]} markRead={vi.fn()} />)
    expect(screen.getByText('[CS101] Lab')).toBeTruthy()
  })

  it('renders read item with reduced opacity', () => {
    render(<FeedPanel items={[READ]} markRead={vi.fn()} />)
    const item = screen.getByTestId('feed-item-r1')
    expect(item.style.opacity).toBe('0.45')
  })

  it('calls markRead when unread item is clicked', () => {
    const markRead = vi.fn()
    render(<FeedPanel items={[UNREAD]} markRead={markRead} />)
    fireEvent.click(screen.getByTestId('feed-item-u1'))
    expect(markRead).toHaveBeenCalledWith('u1')
  })

  it('does NOT call markRead when read item is clicked', () => {
    const markRead = vi.fn()
    render(<FeedPanel items={[READ]} markRead={markRead} />)
    fireEvent.click(screen.getByTestId('feed-item-r1'))
    expect(markRead).not.toHaveBeenCalled()
  })
})
