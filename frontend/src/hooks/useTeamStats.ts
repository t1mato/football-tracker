import { useQuery } from '@tanstack/react-query'

export interface TeamStatsRow {
  position: number
  played_games: number
  won: number
  draw: number
  lost: number
  goals_for: number
  goals_against: number
  goal_difference: number
  points: number
}

interface TeamStatsResponse {
  stats: TeamStatsRow | null
  message: string | null
}

async function fetchTeamStats(
  teamId: number,
  league: string,
  season: number
): Promise<TeamStatsResponse> {
  const response = await fetch(`/api/teams/${teamId}/stats?league=${league}&season=${season}`)
  if (!response.ok) throw new Error(`GET stats failed: ${response.status}`)
  return response.json()
}

export function useTeamStats(
  teamId: number | null,
  league: string,
  season: number | undefined,
  enabled: boolean
) {
  return useQuery({
    queryKey: ['teams', teamId, 'stats', league, season],
    queryFn: () => fetchTeamStats(teamId as number, league, season as number),
    enabled: enabled && teamId !== null && season !== undefined,
  })
}

export interface PositionPoint {
  matchday: number
  position: number
}

async function fetchPositionHistory(
  teamId: number,
  league: string,
  season: number
): Promise<PositionPoint[]> {
  const response = await fetch(
    `/api/teams/${teamId}/position-history?league=${league}&season=${season}`
  )
  if (!response.ok) throw new Error(`GET position-history failed: ${response.status}`)
  return response.json()
}

export function useTeamPositionHistory(
  teamId: number | null,
  league: string,
  season: number | undefined,
  enabled: boolean
) {
  return useQuery({
    queryKey: ['teams', teamId, 'position-history', league, season],
    queryFn: () => fetchPositionHistory(teamId as number, league, season as number),
    enabled: enabled && teamId !== null && season !== undefined,
  })
}
