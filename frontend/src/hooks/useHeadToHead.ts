import { useQuery } from '@tanstack/react-query'

export interface HeadToHeadRecord {
  team_1_wins: number
  team_2_wins: number
  draws: number
  matches_played: number
  team_1_goals: number
  team_2_goals: number
}

async function fetchHeadToHead(
  teamId: number,
  opponentId: number
): Promise<HeadToHeadRecord | null> {
  const response = await fetch(`/api/teams/${teamId}/head-to-head/${opponentId}`)
  if (!response.ok) throw new Error(`GET head-to-head failed: ${response.status}`)
  return response.json()
}

export function useHeadToHead(
  teamId: number | null,
  opponentId: number | undefined,
  enabled: boolean
) {
  return useQuery({
    queryKey: ['teams', teamId, 'head-to-head', opponentId],
    queryFn: () => fetchHeadToHead(teamId as number, opponentId as number),
    enabled: enabled && teamId !== null && opponentId !== undefined,
  })
}

export interface HeadToHeadMatch {
  kickoff_utc: string
  kickoff_time_confirmed: boolean
  competition_name: string
  home_team_name: string
  away_team_name: string
  full_time_home: number | null
  full_time_away: number | null
}

async function fetchHeadToHeadMatches(
  teamId: number,
  opponentId: number
): Promise<HeadToHeadMatch[]> {
  const response = await fetch(`/api/teams/${teamId}/head-to-head/${opponentId}/matches`)
  if (!response.ok) throw new Error(`GET head-to-head matches failed: ${response.status}`)
  return response.json()
}

export function useHeadToHeadMatches(
  teamId: number | null,
  opponentId: number | undefined,
  enabled: boolean
) {
  return useQuery({
    queryKey: ['teams', teamId, 'head-to-head', opponentId, 'matches'],
    queryFn: () => fetchHeadToHeadMatches(teamId as number, opponentId as number),
    enabled: enabled && teamId !== null && opponentId !== undefined,
  })
}
