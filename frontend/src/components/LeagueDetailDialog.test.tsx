import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import { server } from '../test/mocks/server'
import { LeagueDetailDialog } from './LeagueDetailDialog'

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  )
}

describe('LeagueDetailDialog', () => {
  let standingsCallCount = 0
  let resultsCallCount = 0

  beforeEach(() => {
    standingsCallCount = 0
    resultsCallCount = 0
    server.use(
      http.get('/api/leagues/PL/seasons', () =>
        HttpResponse.json([{ season_id: 2526, start_date: '2025-08-01', end_date: '2026-05-31' }])
      ),
      http.get('/api/leagues/PL/current-season', () =>
        HttpResponse.json({ season_id: 2526 })
      ),
      http.get('/api/leagues/PL/standings', () => {
        standingsCallCount++
        return HttpResponse.json({ table: [], message: 'No standings yet' })
      }),
      http.get('/api/leagues/PL/results', () => {
        resultsCallCount++
        return HttpResponse.json([])
      })
    )
  })

  it('shows the competition name as the dialog title, not a generic label', async () => {
    renderWithQueryClient(
      <LeagueDetailDialog competitionCode="PL" competitionName="Premier League" onClose={() => {}} />
    )

    expect(await screen.findByRole('heading', { name: 'Premier League' })).toBeInTheDocument()
  })

  it('fetches only the active tab, not every tab, when the dialog opens', async () => {
    renderWithQueryClient(
      <LeagueDetailDialog competitionCode="PL" competitionName="Premier League" onClose={() => {}} />
    )

    await waitFor(() => expect(standingsCallCount).toBe(1))
    expect(resultsCallCount).toBe(0)
  })

  it('fetches a tab only once it is actually clicked', async () => {
    renderWithQueryClient(
      <LeagueDetailDialog competitionCode="PL" competitionName="Premier League" onClose={() => {}} />
    )
    await waitFor(() => expect(standingsCallCount).toBe(1))

    await userEvent.click(await screen.findByRole('tab', { name: /recent results/i }))

    await waitFor(() => expect(resultsCallCount).toBe(1))
  })
})
