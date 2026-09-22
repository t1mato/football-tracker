import { useQuery } from '@tanstack/react-query'

export interface AssistRow {
  rank: number
  player_name: string
  team_name: string
  crest: string | null
  assists: number
  played_matches: number
}

async function fetchAssists(code: string, season: number): Promise<AssistRow[]> {
  const response = await fetch(`/api/leagues/${code}/assists?season=${season}`)
  if (!response.ok) throw new Error(`GET assists failed: ${response.status}`)
  return response.json()
}

export function useLeagueAssists(code: string, season: number | undefined, enabled: boolean) {
  return useQuery({
    queryKey: ['leagues', code, 'assists', season],
    queryFn: () => fetchAssists(code, season as number),
    enabled: enabled && season !== undefined,
  })
}
