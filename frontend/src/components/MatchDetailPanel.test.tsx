import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { server } from '../test/mocks/server'
import { MatchDetailPanel } from './MatchDetailPanel'

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

describe('MatchDetailPanel', () => {
  it('renders venue and weather detail for the given match', async () => {
    server.use(
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

    renderWithQueryClient(<MatchDetailPanel matchId={1001} />)

    expect(await screen.findByText('Anfield')).toBeInTheDocument()
    expect(await screen.findByText(/61,276/)).toBeInTheDocument()
  })

  it('shows a not-yet-resolved message when the venue needs review', async () => {
    server.use(
      http.get('/api/matches/1002', () =>
        HttpResponse.json({
          match_id: 1002,
          venue_display_name: null,
          venue_needs_review: true,
          capacity: null,
          latitude: null,
          longitude: null,
          temperature_2m: null,
          precipitation: null,
          wind_speed_10m: null,
          weather_data_type: null,
        })
      )
    )

    renderWithQueryClient(<MatchDetailPanel matchId={1002} />)

    expect(await screen.findByText(/venue location not yet resolved/i)).toBeInTheDocument()
  })
})
