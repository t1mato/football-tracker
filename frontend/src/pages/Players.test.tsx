import { render, screen } from '@testing-library/react'
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

describe('Players', () => {
  beforeEach(() => {
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
      http.get('/api/players/1/scoring-history', () => HttpResponse.json([]))
    )
  })

  it('renders the player directory', async () => {
    renderWithQueryClient(<Players />)

    expect(await screen.findByText('Alice Smith')).toBeInTheDocument()
  })

  it('opens the detail dialog for the clicked player', async () => {
    renderWithQueryClient(<Players />)
    const row = await screen.findByText('Alice Smith')

    await userEvent.click(row)

    expect(await screen.findByRole('heading', { name: 'Alice Smith' })).toBeInTheDocument()
  })
})
