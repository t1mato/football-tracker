import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import { server } from '../test/mocks/server'
import { TeamDetailDialog } from './TeamDetailDialog'

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

describe('TeamDetailDialog', () => {
  let formCallCount = 0
  let upcomingCallCount = 0

  beforeEach(() => {
    formCallCount = 0
    upcomingCallCount = 0
    server.use(
      http.get('/api/teams/1/form', () => {
        formCallCount++
        return HttpResponse.json([])
      }),
      http.get('/api/teams/1/upcoming', () => {
        upcomingCallCount++
        return HttpResponse.json([])
      })
    )
  })

  it('shows the team name as the dialog title', async () => {
    renderWithQueryClient(
      <TeamDetailDialog
        teamId={1}
        teamName="Test United"
        leagueCode="PL"
        leagueSeasonId={2526}
        onClose={() => {}}
      />
    )

    expect(await screen.findByRole('heading', { name: 'Test United' })).toBeInTheDocument()
  })

  it('fetches only the active tab, not every tab, when the dialog opens', async () => {
    renderWithQueryClient(
      <TeamDetailDialog
        teamId={1}
        teamName="Test United"
        leagueCode="PL"
        leagueSeasonId={2526}
        onClose={() => {}}
      />
    )

    await waitFor(() => expect(formCallCount).toBe(1))
    expect(upcomingCallCount).toBe(0)
  })

  it('fetches fixtures only once the Fixtures tab is clicked', async () => {
    renderWithQueryClient(
      <TeamDetailDialog
        teamId={1}
        teamName="Test United"
        leagueCode="PL"
        leagueSeasonId={2526}
        onClose={() => {}}
      />
    )
    await waitFor(() => expect(formCallCount).toBe(1))

    await userEvent.click(await screen.findByRole('tab', { name: /fixtures/i }))

    await waitFor(() => expect(upcomingCallCount).toBe(1))
  })

  it('does not fetch anything when teamId is null', async () => {
    renderWithQueryClient(
      <TeamDetailDialog
        teamId={null}
        leagueCode="PL"
        leagueSeasonId={2526}
        onClose={() => {}}
      />
    )

    await new Promise((resolve) => setTimeout(resolve, 50))
    expect(formCallCount).toBe(0)
  })
})
