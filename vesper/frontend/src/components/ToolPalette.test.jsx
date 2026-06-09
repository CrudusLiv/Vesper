import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, test, vi } from 'vitest'
import ToolPalette from './ToolPalette.jsx'

test('renders all seven tool buttons', () => {
  render(<ToolPalette onSelect={() => {}} />)
  expect(screen.getByRole('button', { name: /note/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /finance/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /schedule/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /search/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /files/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /browser/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /system/i })).toBeInTheDocument()
})

test('clicking a tool button calls onSelect with the tool id', async () => {
  const onSelect = vi.fn()
  render(<ToolPalette onSelect={onSelect} />)
  await userEvent.click(screen.getByRole('button', { name: /note/i }))
  expect(onSelect).toHaveBeenCalledWith('notes')
})

test('clicking finance calls onSelect with finance', async () => {
  const onSelect = vi.fn()
  render(<ToolPalette onSelect={onSelect} />)
  await userEvent.click(screen.getByRole('button', { name: /finance/i }))
  expect(onSelect).toHaveBeenCalledWith('finance')
})

test('has toolbar role', () => {
  render(<ToolPalette onSelect={() => {}} />)
  expect(screen.getByRole('toolbar')).toBeInTheDocument()
})
