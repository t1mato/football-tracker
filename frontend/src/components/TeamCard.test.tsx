import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { TeamCard } from './TeamCard'

describe('TeamCard', () => {
  it('renders the team name and crest, and calls onView when clicked', async () => {
    const onView = vi.fn()
    render(
      <TeamCard
        team={{ team_id: 1, team_name: 'Test United', crest: 'crest.png' }}
        onView={onView}
      />
    )

    expect(screen.getByText('Test United')).toBeInTheDocument()
    expect(screen.getByRole('img')).toHaveAttribute('src', 'crest.png')

    await userEvent.click(screen.getByRole('button', { name: /test united/i }))

    expect(onView).toHaveBeenCalledOnce()
  })

  it('renders without a crest image when crest is null', () => {
    render(
      <TeamCard team={{ team_id: 2, team_name: 'No Crest FC', crest: null }} onView={() => {}} />
    )

    expect(screen.getByText('No Crest FC')).toBeInTheDocument()
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
  })
})
