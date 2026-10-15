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
  it('shows the home team\'s venue name and nothing else', async () => {
    server.use(
      http.get('/api/matches/1001', () =>
        HttpResponse.json({ match_id: 1001, venue_name: 'Anfield' })
      )
    )

    renderWithQueryClient(<MatchDetailPanel matchId={1001} />)

    expect(await screen.findByText('Anfield')).toBeInTheDocument()
    expect(screen.queryByText(/weather/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/capacity/i)).not.toBeInTheDocument()
  })

  it('says the venue is unavailable when the API reports none', async () => {
    server.use(
      http.get('/api/matches/1002', () =>
        HttpResponse.json({ match_id: 1002, venue_name: null })
      )
    )

    renderWithQueryClient(<MatchDetailPanel matchId={1002} />)

    expect(await screen.findByText(/venue not available/i)).toBeInTheDocument()
  })
})
