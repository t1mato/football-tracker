import { useQuery } from '@tanstack/react-query'

export interface StreakRow {
  team_id: number
  team_name: string
  current_win_streak: number
  current_unbeaten_streak: number
  longest_win_streak: number
  longest_unbeaten_streak: number
}

async function fetchStreaks(code: string): Promise<StreakRow[]> {
  const response = await fetch(`/api/leagues/${code}/streaks`)
  if (!response.ok) throw new Error(`GET streaks failed: ${response.status}`)
  return response.json()
}

async function fetchTeamsInSeason(code: string, season: number): Promise<{ team_id: number }[]> {
  const response = await fetch(`/api/leagues/${code}/teams-in-season?season=${season}`)
  if (!response.ok) throw new Error(`GET teams-in-season failed: ${response.status}`)
  return response.json()
}

export function useLeagueStreaks(code: string, active: boolean) {
  return useQuery({
    queryKey: ['leagues', code, 'streaks'],
    queryFn: () => fetchStreaks(code),
    enabled: active,
  })
}

export function useTeamsInSeason(code: string, season: number | undefined, active: boolean) {
  return useQuery({
    queryKey: ['leagues', code, 'teams-in-season', season],
    queryFn: () => fetchTeamsInSeason(code, season as number),
    enabled: active && season !== undefined,
  })
}
