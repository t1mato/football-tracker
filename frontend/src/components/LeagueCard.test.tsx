import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { LeagueCard } from './LeagueCard'

const competition = {
  competition_code: 'PL',
  competition_name: 'Premier League',
  area_name: 'England',
  emblem: 'https://crests.football-data.org/PL.png',
  area_flag: 'https://crests.football-data.org/ENG.svg',
}

describe('LeagueCard', () => {
  it('renders the competition name and country', () => {
    render(<LeagueCard competition={competition} onView={() => {}} />)

    expect(screen.getByText('Premier League')).toBeInTheDocument()
    expect(screen.getByText('England')).toBeInTheDocument()
  })

  it('calls onView when the View button is clicked', async () => {
    const onView = vi.fn()
    render(<LeagueCard competition={competition} onView={onView} />)

    await userEvent.click(screen.getByRole('button', { name: /view/i }))

    expect(onView).toHaveBeenCalledOnce()
  })
})
