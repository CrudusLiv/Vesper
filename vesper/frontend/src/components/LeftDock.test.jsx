import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, test, vi } from 'vitest'
import LeftDock from './LeftDock.jsx'

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
