import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { server } from '../test/mocks/server'
import { PlayerDetailDialog } from './PlayerDetailDialog'

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

describe('PlayerDetailDialog', () => {
  it('renders bio and scoring history for an open player', async () => {
    server.use(
      http.get('/api/players/1', () =>
        HttpResponse.json({
          player_name: 'Alice Smith',
          position: 'Forward',
          nationality: 'England',
          date_of_birth: '2000-06-15',
          team_name: 'Team A',
          crest: 'a.png',
        })
      ),
      http.get('/api/players/1/scoring-history', () =>
        HttpResponse.json([
          {
            competition_name: 'Premier League',
            start_date: '2025-08-01',
            end_date: '2026-05-31',
            goals: 10,
            assists: 3,
            played_matches: 20,
            penalties: 2,
          },
        ])
      )
    )

    renderWithQueryClient(<PlayerDetailDialog playerId={1} onClose={() => {}} />)

    expect(await screen.findByRole('heading', { name: 'Alice Smith' })).toBeInTheDocument()
    expect(await screen.findByText('Premier League')).toBeInTheDocument()
  })

  it('does not fetch anything when playerId is null', async () => {
    let bioCallCount = 0
    server.use(
      http.get('/api/players/:id', () => {
        bioCallCount++
        return HttpResponse.json({})
      })
    )

    renderWithQueryClient(<PlayerDetailDialog playerId={null} onClose={() => {}} />)
    await new Promise((resolve) => setTimeout(resolve, 50))

    expect(bioCallCount).toBe(0)
  })

  it('shows "Player not found" for an unknown id', async () => {
    server.use(http.get('/api/players/999', () => new HttpResponse(null, { status: 404 })))

    renderWithQueryClient(<PlayerDetailDialog playerId={999} onClose={() => {}} />)

    expect(await screen.findByText('Player not found')).toBeInTheDocument()
  })
})
