import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { server } from '../test/mocks/server'
import { GoldenBootTab } from './GoldenBootTab'

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

const COMPETITIONS = [
  {
    competition_code: 'PL',
    competition_name: 'Premier League',
    area_name: 'England',
    emblem: null,
    area_flag: null,
  },
  {
    competition_code: 'BL1',
    competition_name: 'Bundesliga',
    area_name: 'Germany',
    emblem: null,
    area_flag: null,
  },
]

describe('GoldenBootTab', () => {
  it('does not fetch anything while inactive', async () => {
    let competitionsCallCount = 0
    server.use(
      http.get('/api/competitions', () => {
        competitionsCallCount++
        return HttpResponse.json(COMPETITIONS)
      })
    )

    renderWithQueryClient(<GoldenBootTab active={false} />)
    await new Promise((resolve) => setTimeout(resolve, 50))

    expect(competitionsCallCount).toBe(0)
  })

  it('shows scorers for the first competition once active', async () => {
    server.use(
      http.get('/api/competitions', () => HttpResponse.json(COMPETITIONS)),
      http.get('/api/leagues/PL/current-season', () => HttpResponse.json({ season_id: 2526 })),
      http.get('/api/leagues/PL/scorers', () =>
        HttpResponse.json([
          {
            rank: 1,
            player_name: 'Top Scorer',
            team_name: 'Team A',
            crest: null,
            goals: 20,
            assists: 5,
            played_matches: 30,
            penalties: 3,
          },
        ])
      )
    )

    renderWithQueryClient(<GoldenBootTab active={true} />)

    expect(await screen.findByText('Top Scorer')).toBeInTheDocument()
  })

  it('fetches a new leaderboard when a different competition is selected', async () => {
    server.use(
      http.get('/api/competitions', () => HttpResponse.json(COMPETITIONS)),
      http.get('/api/leagues/PL/current-season', () => HttpResponse.json({ season_id: 2526 })),
      http.get('/api/leagues/PL/scorers', () => HttpResponse.json([])),
      http.get('/api/leagues/BL1/current-season', () => HttpResponse.json({ season_id: 2522 })),
      http.get('/api/leagues/BL1/scorers', () =>
        HttpResponse.json([
          {
            rank: 1,
            player_name: 'Bundesliga Scorer',
            team_name: 'Team C',
            crest: null,
            goals: 15,
            assists: 2,
            played_matches: 25,
            penalties: 1,
          },
        ])
      )
    )

    renderWithQueryClient(<GoldenBootTab active={true} />)
    await screen.findByRole('combobox')

    await userEvent.selectOptions(screen.getByRole('combobox'), 'Bundesliga')

    expect(await screen.findByText('Bundesliga Scorer')).toBeInTheDocument()
  })
})
