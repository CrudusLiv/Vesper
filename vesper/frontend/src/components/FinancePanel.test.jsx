import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, test, vi } from 'vitest'
import FinancePanel from './FinancePanel.jsx'

test('submitting logs the expense and shows the returned totals', async () => {
  const onLog = vi.fn().mockResolvedValue({ month_total: 12.5, category_total: 12.5, currency: 'RM', date: 'x' })
  const onLoadSummary = vi.fn().mockResolvedValue({ summary: '' })
  render(<FinancePanel onLog={onLog} onLoadSummary={onLoadSummary} />)
  await userEvent.type(screen.getByPlaceholderText(/amount/i), '12.5')
  await userEvent.type(screen.getByPlaceholderText(/category/i), 'food')
  await userEvent.click(screen.getByRole('button', { name: /log expense/i }))
  expect(onLog).toHaveBeenCalledWith(12.5, 'food', '')
  expect(await screen.findByText(/RM/)).toBeInTheDocument()
})

test('rejects a non-positive amount without calling onLog', async () => {
  const onLog = vi.fn()
  const onLoadSummary = vi.fn().mockResolvedValue({ summary: '' })
  render(<FinancePanel onLog={onLog} onLoadSummary={onLoadSummary} />)
  await userEvent.type(screen.getByPlaceholderText(/amount/i), '0')
  await userEvent.type(screen.getByPlaceholderText(/category/i), 'food')
  await userEvent.click(screen.getByRole('button', { name: /log expense/i }))
  expect(onLog).not.toHaveBeenCalled()
  expect(screen.getByText(/positive/i)).toBeInTheDocument()
})

test('loads the month summary on mount', async () => {
  const onLoadSummary = vi.fn().mockResolvedValue({ summary: 'June 2026 -- RM5.00 total' })
  render(<FinancePanel onLog={vi.fn()} onLoadSummary={onLoadSummary} />)
  expect(await screen.findByText(/June 2026/)).toBeInTheDocument()
})
