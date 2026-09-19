import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

describe('test toolchain', () => {
  it('renders a basic element', () => {
    render(<div>Toolchain works</div>)
    expect(screen.getByText('Toolchain works')).toBeInTheDocument()
  })
})
