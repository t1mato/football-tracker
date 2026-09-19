import { useQuery } from '@tanstack/react-query'

export interface StandingsRow {
  position: number
  team_name: string
  crest: string | null
  played_games: number
  won: number
  draw: number
  lost: number
  goals_for: number
  goals_against: number
  goal_difference: number
  points: number
  team_id: number
}

interface StandingsResponse {
  table: StandingsRow[] | null
  message: string | null
}

async function fetchStandings(code: string, season: number): Promise<StandingsResponse> {
  const response = await fetch(`/api/leagues/${code}/standings?season=${season}`)
  if (!response.ok) throw new Error(`GET standings failed: ${response.status}`)
  return response.json()
}

export function useStandings(code: string, season: number | undefined, enabled: boolean) {
  return useQuery({
    queryKey: ['leagues', code, 'standings', season],
    queryFn: () => fetchStandings(code, season as number),
    enabled: enabled && season !== undefined,
  })
}

export interface ReconstructedRow {
  group_name: string | null
  position: number
  team_name: string
  points: number
  goal_difference: number
  goals_for: number
}

async function fetchReconstructedStandings(
  code: string,
  season: number
): Promise<ReconstructedRow[]> {
  const response = await fetch(`/api/leagues/${code}/reconstructed-standings?season=${season}`)
  if (!response.ok) throw new Error(`GET reconstructed-standings failed: ${response.status}`)
  return response.json()
}

export function useReconstructedStandings(
  code: string,
  season: number | undefined,
  enabled: boolean
) {
  return useQuery({
    queryKey: ['leagues', code, 'reconstructed-standings', season],
    queryFn: () => fetchReconstructedStandings(code, season as number),
    enabled: enabled && season !== undefined,
  })
}
