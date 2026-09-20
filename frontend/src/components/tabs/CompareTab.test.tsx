import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import { server } from '../../test/mocks/server'
import { CompareTab } from './CompareTab'

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

describe('CompareTab', () => {
  let headToHeadCallCount = 0
  let matchesCallCount = 0

  beforeEach(() => {
    headToHeadCallCount = 0
    matchesCallCount = 0
    server.use(
      http.get('/api/teams/all', () =>
        HttpResponse.json([
          { team_id: 1, team_name: 'Team A' },
          { team_id: 2, team_name: 'Team B' },
        ])
      ),
      http.get('/api/teams/1/head-to-head/2', () => {
        headToHeadCallCount++
        return HttpResponse.json({
          team_1_wins: 2,
          team_2_wins: 1,
          draws: 0,
          matches_played: 3,
          team_1_goals: 5,
          team_2_goals: 3,
        })
      }),
      http.get('/api/teams/1/head-to-head/2/matches', () => {
        matchesCallCount++
        return HttpResponse.json([])
      })
    )
  })

  it('fetches nothing until an opponent is actually picked', async () => {
    renderWithQueryClient(<CompareTab teamId={1} active={true} />)

    await screen.findByRole('combobox')
    await new Promise((resolve) => setTimeout(resolve, 50))

    expect(headToHeadCallCount).toBe(0)
    expect(matchesCallCount).toBe(0)
  })

  it('fetches the head-to-head record once an opponent is picked, then the match list', async () => {
    renderWithQueryClient(<CompareTab teamId={1} active={true} />)

    const select = await screen.findByRole('combobox')
    await userEvent.selectOptions(select, 'Team B')

    await waitFor(() => expect(headToHeadCallCount).toBe(1))
    await waitFor(() => expect(matchesCallCount).toBe(1))
    expect(await screen.findByText(/played 3/i)).toBeInTheDocument()
  })

  it('does not list the team itself as a possible opponent', async () => {
    renderWithQueryClient(<CompareTab teamId={1} active={true} />)

    await screen.findByRole('combobox')

    expect(screen.queryByRole('option', { name: 'Team A' })).not.toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Team B' })).toBeInTheDocument()
  })

  it('shows a never-played message and skips the match list when the teams have no head-to-head record', async () => {
    server.use(
      http.get('/api/teams/1/head-to-head/2', () => {
        headToHeadCallCount++
        return HttpResponse.json(null)
      })
    )

    renderWithQueryClient(<CompareTab teamId={1} active={true} />)

    const select = await screen.findByRole('combobox')
    await userEvent.selectOptions(select, 'Team B')

    await waitFor(() => expect(headToHeadCallCount).toBe(1))
    expect(
      await screen.findByText(/these two teams haven't played each other yet/i)
    ).toBeInTheDocument()

    await new Promise((resolve) => setTimeout(resolve, 50))
    expect(matchesCallCount).toBe(0)
  })
})
