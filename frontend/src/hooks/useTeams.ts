import { useQuery } from '@tanstack/react-query'

export interface TeamRow {
  team_id: number
  team_name: string
  crest: string | null
}

async function fetchTeamsForLeague(league: string, season: number): Promise<TeamRow[]> {
  const response = await fetch(`/api/teams?league=${league}&season=${season}`)
  if (!response.ok) throw new Error(`GET teams failed: ${response.status}`)
  return response.json()
}

export function useTeams(league: string, season: number | undefined, enabled: boolean) {
  return useQuery({
    queryKey: ['teams', 'league', league, season],
    queryFn: () => fetchTeamsForLeague(league, season as number),
    enabled: enabled && league !== '' && season !== undefined,
  })
}

async function fetchAllTeams(): Promise<TeamRow[]> {
  const response = await fetch('/api/teams/all')
  if (!response.ok) throw new Error(`GET teams/all failed: ${response.status}`)
  return response.json()
}

export function useAllTeams(enabled: boolean) {
  return useQuery({
    queryKey: ['teams', 'all'],
    queryFn: fetchAllTeams,
    enabled,
  })
}
