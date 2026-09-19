import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { server } from '../../test/mocks/server'
import { RecentResultsTab } from './RecentResultsTab'

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

describe('RecentResultsTab', () => {
  it('expands match detail on row click and collapses it on a second click', async () => {
    server.use(
      http.get('/api/leagues/PL/results', () =>
        HttpResponse.json([
          {
            match_id: 1001,
            kickoff_utc: '2025-09-01T15:00:00Z',
            kickoff_time_confirmed: true,
            home_team_name: 'Liverpool',
            home_crest: null,
            away_team_name: 'Everton',
            away_crest: null,
            full_time_home: 2,
            full_time_away: 1,
          },
        ])
      ),
      http.get('/api/matches/1001', () =>
        HttpResponse.json({
          match_id: 1001,
          venue_display_name: 'Anfield',
          venue_needs_review: false,
          capacity: 61276,
          latitude: 53.4308,
          longitude: -2.9608,
          temperature_2m: 12.5,
          precipitation: 0,
          wind_speed_10m: 15,
          weather_data_type: 'forecast',
        })
      )
    )

    renderWithQueryClient(
      <RecentResultsTab competitionCode="PL" seasonId={2526} active={true} />
    )

    const row = await screen.findByText('Liverpool')
    expect(screen.queryByText('Anfield')).not.toBeInTheDocument()

    await userEvent.click(row)
    expect(await screen.findByText('Anfield')).toBeInTheDocument()

    await userEvent.click(row)
    expect(screen.queryByText('Anfield')).not.toBeInTheDocument()
  })
})
