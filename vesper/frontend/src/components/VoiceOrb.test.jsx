import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'
import VoiceOrb from './VoiceOrb.jsx'

test('applies the state as a class and shows the state label', () => {
  const { rerender } = render(<VoiceOrb state="idle" />)
  expect(screen.getByTestId('orb')).toHaveClass('orb', 'orb-idle')
  expect(screen.getByText(/idle/i)).toBeInTheDocument()

  rerender(<VoiceOrb state="thinking" />)
  expect(screen.getByTestId('orb')).toHaveClass('orb-thinking')
})
