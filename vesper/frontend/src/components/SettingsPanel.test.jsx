import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, describe, test, vi, beforeEach } from 'vitest'
import SettingsPanel from './SettingsPanel.jsx'
import { useSettings } from '../hooks/useSettings.js'

vi.mock('../hooks/useSettings.js')
vi.mock('./FloatingPanel.jsx', () => ({
  FloatingPanel: ({ children }) => <div>{children}</div>
}))

describe('SettingsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const mockSettings = {
    active_hours_start: '09:00',
    active_hours_end: '22:00',
    heartbeat_interval_minutes: 30,
    features: { inbox: true, reflect: false }
  }

  test('renders settings after load completes', () => {
    useSettings.mockReturnValue({
      settings: mockSettings,
      load: vi.fn(),
      save: vi.fn(),
      loading: false,
      error: null,
    })

    render(<SettingsPanel />)
    expect(screen.getByDisplayValue('09:00')).toBeInTheDocument()
    expect(screen.getByDisplayValue(30)).toBeInTheDocument()
  })

  test('calls load on mount', () => {
    const mockLoad = vi.fn()
    useSettings.mockReturnValue({
      settings: mockSettings,
      load: mockLoad,
      save: vi.fn(),
      loading: false,
      error: null,
    })

    render(<SettingsPanel />)
    expect(mockLoad).toHaveBeenCalled()
  })

  test('returns null before settings load', () => {
    useSettings.mockReturnValue({
      settings: null,
      load: vi.fn(),
      save: vi.fn(),
      loading: true,
      error: null,
    })

    const { container } = render(<SettingsPanel />)
    expect(container.firstChild).toBeNull()
  })

  test('updates form when settings change', () => {
    const { rerender } = render(<SettingsPanel />)

    useSettings.mockReturnValue({
      settings: mockSettings,
      load: vi.fn(),
      save: vi.fn(),
      loading: false,
      error: null,
    })

    rerender(<SettingsPanel />)
    expect(screen.getByDisplayValue('09:00')).toBeInTheDocument()
  })

  test('toggles feature checkbox', async () => {
    useSettings.mockReturnValue({
      settings: mockSettings,
      load: vi.fn(),
      save: vi.fn(),
      loading: false,
      error: null,
    })

    render(<SettingsPanel />)
    const checkboxes = screen.getAllByRole('checkbox')
    expect(checkboxes).toHaveLength(2)
    expect(checkboxes[0]).toBeChecked()
    expect(checkboxes[1]).not.toBeChecked()

    await userEvent.click(checkboxes[0])
    expect(checkboxes[0]).not.toBeChecked()
  })

  test('Save button disabled when no changes', () => {
    useSettings.mockReturnValue({
      settings: mockSettings,
      load: vi.fn(),
      save: vi.fn(),
      loading: false,
      error: null,
    })

    render(<SettingsPanel />)
    const saveBtn = screen.getByRole('button', { name: /save/i })
    expect(saveBtn).toBeDisabled()
  })

  test('Save button enabled after changes', async () => {
    useSettings.mockReturnValue({
      settings: mockSettings,
      load: vi.fn(),
      save: vi.fn(),
      loading: false,
      error: null,
    })

    render(<SettingsPanel />)
    const startInput = screen.getByDisplayValue('09:00')

    await userEvent.clear(startInput)
    await userEvent.type(startInput, '10:00')

    const saveBtn = screen.getByRole('button', { name: /save/i })
    expect(saveBtn).not.toBeDisabled()
  })

  test('Reset button disabled when no changes', () => {
    useSettings.mockReturnValue({
      settings: mockSettings,
      load: vi.fn(),
      save: vi.fn(),
      loading: false,
      error: null,
    })

    render(<SettingsPanel />)
    const resetBtn = screen.getByRole('button', { name: /reset/i })
    expect(resetBtn).toBeDisabled()
  })

  test('Reset button reverts changes', async () => {
    useSettings.mockReturnValue({
      settings: mockSettings,
      load: vi.fn(),
      save: vi.fn(),
      loading: false,
      error: null,
    })

    render(<SettingsPanel />)
    const startInput = screen.getByDisplayValue('09:00')

    await userEvent.clear(startInput)
    await userEvent.type(startInput, '10:00')
    expect(screen.getByDisplayValue('10:00')).toBeInTheDocument()

    const resetBtn = screen.getByRole('button', { name: /reset/i })
    await userEvent.click(resetBtn)
    expect(screen.getByDisplayValue('09:00')).toBeInTheDocument()
  })

  test('calls save with updated settings', async () => {
    const mockSave = vi.fn().mockResolvedValue(mockSettings)
    useSettings.mockReturnValue({
      settings: mockSettings,
      load: vi.fn(),
      save: mockSave,
      loading: false,
      error: null,
    })

    render(<SettingsPanel />)
    const startInput = screen.getByDisplayValue('09:00')

    await userEvent.clear(startInput)
    await userEvent.type(startInput, '10:00')

    const saveBtn = screen.getByRole('button', { name: /save/i })
    await userEvent.click(saveBtn)

    await waitFor(() => {
      expect(mockSave).toHaveBeenCalledWith(expect.objectContaining({
        active_hours_start: '10:00'
      }))
    })
  })

  test('shows saving state during save', async () => {
    const mockSave = vi.fn(() => new Promise(resolve => setTimeout(resolve, 100)))
    useSettings.mockReturnValue({
      settings: mockSettings,
      load: vi.fn(),
      save: mockSave,
      loading: false,
      error: null,
    })

    render(<SettingsPanel />)
    const startInput = screen.getByDisplayValue('09:00')

    await userEvent.clear(startInput)
    await userEvent.type(startInput, '10:00')

    const saveBtn = screen.getByRole('button', { name: /save/i })
    await userEvent.click(saveBtn)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /saving/i })).toBeInTheDocument()
    })
  })

  test('disables Save button while saving', async () => {
    const mockSave = vi.fn(() => new Promise(resolve => setTimeout(resolve, 100)))
    useSettings.mockReturnValue({
      settings: mockSettings,
      load: vi.fn(),
      save: mockSave,
      loading: false,
      error: null,
    })

    render(<SettingsPanel />)
    const startInput = screen.getByDisplayValue('09:00')

    await userEvent.clear(startInput)
    await userEvent.type(startInput, '10:00')

    const saveBtn = screen.getByRole('button', { name: /save/i })
    await userEvent.click(saveBtn)

    await waitFor(() => {
      expect(saveBtn).toBeDisabled()
    })
  })

  test('displays error message on save failure', async () => {
    const mockSave = vi.fn().mockRejectedValue(new Error('Network error'))
    useSettings.mockReturnValue({
      settings: mockSettings,
      load: vi.fn(),
      save: mockSave,
      loading: false,
      error: null,
    })

    render(<SettingsPanel />)
    const startInput = screen.getByDisplayValue('09:00')

    await userEvent.clear(startInput)
    await userEvent.type(startInput, '10:00')

    const saveBtn = screen.getByRole('button', { name: /save/i })
    await userEvent.click(saveBtn)

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument()
    })
  })

  test('changes number input for heartbeat interval', async () => {
    useSettings.mockReturnValue({
      settings: mockSettings,
      load: vi.fn(),
      save: vi.fn(),
      loading: false,
      error: null,
    })

    render(<SettingsPanel />)
    const heartbeatInput = screen.getByRole('spinbutton')

    await userEvent.clear(heartbeatInput)
    await userEvent.type(heartbeatInput, '45')

    expect(heartbeatInput).toHaveValue(45)
    const saveBtn = screen.getByRole('button', { name: /save/i })
    expect(saveBtn).not.toBeDisabled()
  })
})
