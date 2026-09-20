import { useQuery } from '@tanstack/react-query'

export interface TeamStreaksRow {
  current_win_streak: number
  current_unbeaten_streak: number
  longest_win_streak: number
  longest_unbeaten_streak: number
}

interface TeamStreaksResponse {
  streaks: TeamStreaksRow | null
  message: string | null
}

async function fetchTeamStreaks(teamId: number, league: string): Promise<TeamStreaksResponse> {
  const response = await fetch(`/api/teams/${teamId}/streaks?league=${league}`)
  if (!response.ok) throw new Error(`GET streaks failed: ${response.status}`)
  return response.json()
}

export function useTeamStreaks(teamId: number | null, league: string, enabled: boolean) {
  return useQuery({
    queryKey: ['teams', teamId, 'streaks', league],
    queryFn: () => fetchTeamStreaks(teamId as number, league),
    enabled: enabled && teamId !== null,
  })
}
