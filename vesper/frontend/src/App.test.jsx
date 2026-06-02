import { render, screen } from '@testing-library/react'
import App from './App.jsx'

test('renders the Vesper wordmark', () => {
  render(<App />)
  expect(screen.getByText(/vesper/i)).toBeInTheDocument()
})
