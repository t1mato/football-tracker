import { useQuery } from '@tanstack/react-query'

export interface Season {
  season_id: number
  start_date: string
  end_date: string
}

async function fetchSeasons(code: string): Promise<Season[]> {
  const response = await fetch(`/api/leagues/${code}/seasons`)
  if (!response.ok) throw new Error(`GET seasons failed: ${response.status}`)
  return response.json()
}

async function fetchCurrentSeason(code: string): Promise<number> {
  const response = await fetch(`/api/leagues/${code}/current-season`)
  if (!response.ok) throw new Error(`GET current-season failed: ${response.status}`)
  const body: { season_id: number } = await response.json()
  return body.season_id
}

export function useLeagueSeasons(code: string, enabled = true) {
  return useQuery({
    queryKey: ['leagues', code, 'seasons'],
    queryFn: () => fetchSeasons(code),
    enabled: enabled && code !== '',
  })
}

export function useCurrentSeason(code: string, enabled = true) {
  return useQuery({
    queryKey: ['leagues', code, 'current-season'],
    queryFn: () => fetchCurrentSeason(code),
    enabled: enabled && code !== '',
  })
}
