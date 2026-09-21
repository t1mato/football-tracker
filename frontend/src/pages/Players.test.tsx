import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import { server } from '../test/mocks/server'
import { Players } from './Players'

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

const PLAYERS = [
  {
    player_id: 1,
    player_name: 'Alice Smith',
    position: 'Forward',
    nationality: 'England',
    team_name: 'Team A',
    crest: 'a.png',
  },
]

const COMPETITIONS = [
  {
    competition_code: 'PL',
    competition_name: 'Premier League',
    area_name: 'England',
    emblem: null,
    area_flag: null,
  },
]

describe('Players', () => {
  let scorersCallCount = 0

  beforeEach(() => {
    scorersCallCount = 0
    server.use(
      http.get('/api/players', () => HttpResponse.json(PLAYERS)),
      http.get('/api/players/1', () =>
        HttpResponse.json({
          player_name: 'Alice Smith',
          position: 'Forward',
          nationality: 'England',
          date_of_birth: '2000-06-15T00:00:00',
          team_name: 'Team A',
          crest: 'a.png',
        })
      ),
      http.get('/api/players/1/scoring-history', () => HttpResponse.json([])),
      http.get('/api/competitions', () => HttpResponse.json(COMPETITIONS)),
      http.get('/api/leagues/PL/current-season', () => HttpResponse.json({ season_id: 2526 })),
      http.get('/api/leagues/PL/scorers', () => {
        scorersCallCount++
        return HttpResponse.json([])
      })
    )
  })

  it('renders the Directory tab by default', async () => {
    renderWithQueryClient(<Players />)

    expect(await screen.findByText('Alice Smith')).toBeInTheDocument()
    expect(scorersCallCount).toBe(0)
  })

  it('opens the detail dialog for the clicked player', async () => {
    renderWithQueryClient(<Players />)
    const row = await screen.findByText('Alice Smith')

    await userEvent.click(row)

    expect(await screen.findByRole('heading', { name: 'Alice Smith' })).toBeInTheDocument()
  })

  it('activates GoldenBootTab and fetches its data when the tab is switched', async () => {
    renderWithQueryClient(<Players />)
    await screen.findByText('Alice Smith')
    expect(scorersCallCount).toBe(0)

    await userEvent.click(screen.getByRole('tab', { name: 'Golden Boot' }))

    await screen.findByRole('combobox')
    await waitFor(() => expect(scorersCallCount).toBeGreaterThan(0))
  })
})
