import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'
import { server } from '../test/mocks/server'
import { PlayerDirectoryTable } from './PlayerDirectoryTable'

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
  {
    player_id: 2,
    player_name: 'Bob Jones',
    position: 'Defender',
    nationality: 'Spain',
    team_name: 'Team B',
    crest: null,
  },
]

describe('PlayerDirectoryTable', () => {
  it('renders every fetched player', async () => {
    server.use(http.get('/api/players', () => HttpResponse.json(PLAYERS)))
    renderWithQueryClient(<PlayerDirectoryTable onSelectPlayer={() => {}} />)

    expect(await screen.findByText('Alice Smith')).toBeInTheDocument()
    expect(screen.getByText('Bob Jones')).toBeInTheDocument()
  })

  it('filters by search text without refetching', async () => {
    let callCount = 0
    server.use(
      http.get('/api/players', () => {
        callCount++
        return HttpResponse.json(PLAYERS)
      })
    )
    renderWithQueryClient(<PlayerDirectoryTable onSelectPlayer={() => {}} />)
    await screen.findByText('Alice Smith')

    await userEvent.type(screen.getByPlaceholderText('Search by name'), 'Bob')

    expect(screen.queryByText('Alice Smith')).not.toBeInTheDocument()
    expect(screen.getByText('Bob Jones')).toBeInTheDocument()
    expect(callCount).toBe(1)
  })

  it('filters by club', async () => {
    server.use(http.get('/api/players', () => HttpResponse.json(PLAYERS)))
    renderWithQueryClient(<PlayerDirectoryTable onSelectPlayer={() => {}} />)
    await screen.findByText('Alice Smith')

    await userEvent.selectOptions(screen.getByRole('combobox'), 'Team B')

    expect(screen.queryByText('Alice Smith')).not.toBeInTheDocument()
    expect(screen.getByText('Bob Jones')).toBeInTheDocument()
  })

  it('calls onSelectPlayer with the right id when a row is clicked', async () => {
    server.use(http.get('/api/players', () => HttpResponse.json(PLAYERS)))
    const onSelectPlayer = vi.fn()
    renderWithQueryClient(<PlayerDirectoryTable onSelectPlayer={onSelectPlayer} />)
    const row = await screen.findByText('Alice Smith')

    await userEvent.click(row)

    expect(onSelectPlayer).toHaveBeenCalledWith(1)
  })

  it('shows a message when no players match', async () => {
    server.use(http.get('/api/players', () => HttpResponse.json(PLAYERS)))
    renderWithQueryClient(<PlayerDirectoryTable onSelectPlayer={() => {}} />)
    await screen.findByText('Alice Smith')

    await userEvent.type(screen.getByPlaceholderText('Search by name'), 'zzz-no-match')

    expect(
      await screen.findByText('No players match this search/filter.')
    ).toBeInTheDocument()
  })
})
