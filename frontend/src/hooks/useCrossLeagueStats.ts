import { useQuery } from '@tanstack/react-query'

export interface CrossLeagueRow {
  competition_name: string
  decided_matches: number | null
  avg_goals_per_match: number | null
  avg_goal_margin: number | null
  home_win_rate: number | null
}

async function fetchCrossLeagueStats(): Promise<CrossLeagueRow[]> {
  const response = await fetch('/api/cross-league-stats')
  if (!response.ok) throw new Error(`GET cross-league-stats failed: ${response.status}`)
  return response.json()
}

export function useCrossLeagueStats() {
  return useQuery({ queryKey: ['cross-league-stats'], queryFn: fetchCrossLeagueStats })
}
