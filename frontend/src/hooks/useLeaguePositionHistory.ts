import { useQuery } from '@tanstack/react-query'

export interface LeaguePositionPoint {
  team_id: number
  team_name: string
  crest: string | null
  matchday: number
  position: number
}

async function fetchLeaguePositionHistory(
  code: string,
  season: number
): Promise<LeaguePositionPoint[]> {
  const response = await fetch(`/api/leagues/${code}/position-history?season=${season}`)
  if (!response.ok) throw new Error(`GET position-history failed: ${response.status}`)
  return response.json()
}

export function useLeaguePositionHistory(
  code: string,
  season: number | undefined,
  enabled: boolean
) {
  return useQuery({
    queryKey: ['leagues', code, 'position-history', season],
    queryFn: () => fetchLeaguePositionHistory(code, season as number),
    enabled: enabled && season !== undefined,
  })
}
