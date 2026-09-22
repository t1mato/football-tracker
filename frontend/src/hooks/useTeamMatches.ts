import { useQuery } from '@tanstack/react-query'

export interface TeamMatchRow {
  kickoff_utc: string
  kickoff_time_confirmed: boolean
  status?: string
  opponent_team_name: string
  opponent_crest: string | null
  competition_name: string
  competition_emblem?: string | null
  goals_for: number | null
  goals_against: number | null
  result: string | null
}

async function fetchTeamForm(teamId: number): Promise<TeamMatchRow[]> {
  const response = await fetch(`/api/teams/${teamId}/form`)
  if (!response.ok) throw new Error(`GET form failed: ${response.status}`)
  return response.json()
}

export function useTeamForm(teamId: number | null, enabled: boolean) {
  return useQuery({
    queryKey: ['teams', teamId, 'form'],
    queryFn: () => fetchTeamForm(teamId as number),
    enabled: enabled && teamId !== null,
  })
}

async function fetchTeamUpcoming(teamId: number): Promise<TeamMatchRow[]> {
  const response = await fetch(`/api/teams/${teamId}/upcoming`)
  if (!response.ok) throw new Error(`GET upcoming failed: ${response.status}`)
  return response.json()
}

export function useTeamUpcoming(teamId: number | null, enabled: boolean) {
  return useQuery({
    queryKey: ['teams', teamId, 'upcoming'],
    queryFn: () => fetchTeamUpcoming(teamId as number),
    enabled: enabled && teamId !== null,
  })
}
