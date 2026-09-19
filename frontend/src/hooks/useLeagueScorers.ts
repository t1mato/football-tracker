import { useQuery } from '@tanstack/react-query'

export interface ScorerRow {
  rank: number
  player_name: string
  team_name: string
  crest: string | null
  goals: number
  assists: number
  played_matches: number
  penalties: number
}

async function fetchScorers(code: string, season: number): Promise<ScorerRow[]> {
  const response = await fetch(`/api/leagues/${code}/scorers?season=${season}`)
  if (!response.ok) throw new Error(`GET scorers failed: ${response.status}`)
  return response.json()
}

export function useLeagueScorers(code: string, season: number | undefined, enabled: boolean) {
  return useQuery({
    queryKey: ['leagues', code, 'scorers', season],
    queryFn: () => fetchScorers(code, season as number),
    enabled: enabled && season !== undefined,
  })
}
