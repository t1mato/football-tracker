import { useQuery } from '@tanstack/react-query'

export interface MatchRow {
  match_id: number
  kickoff_utc: string
  kickoff_time_confirmed: boolean
  status?: string
  home_team_name: string
  home_crest: string | null
  away_team_name: string
  away_crest: string | null
  full_time_home?: number
  full_time_away?: number
}

async function fetchResults(code: string, season: number): Promise<MatchRow[]> {
  const response = await fetch(`/api/leagues/${code}/results?season=${season}`)
  if (!response.ok) throw new Error(`GET results failed: ${response.status}`)
  return response.json()
}

async function fetchFixtures(code: string, season: number): Promise<MatchRow[]> {
  const response = await fetch(`/api/leagues/${code}/fixtures?season=${season}`)
  if (!response.ok) throw new Error(`GET fixtures failed: ${response.status}`)
  return response.json()
}

export function useLeagueResults(code: string, season: number | undefined, enabled: boolean) {
  return useQuery({
    queryKey: ['leagues', code, 'results', season],
    queryFn: () => fetchResults(code, season as number),
    enabled: enabled && season !== undefined,
  })
}

export function useLeagueFixtures(code: string, season: number | undefined, enabled: boolean) {
  return useQuery({
    queryKey: ['leagues', code, 'fixtures', season],
    queryFn: () => fetchFixtures(code, season as number),
    enabled: enabled && season !== undefined,
  })
}
