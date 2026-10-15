import { useQuery } from '@tanstack/react-query'

export interface MatchDetail {
  match_id: number
  venue_name: string | null
}

async function fetchMatchDetail(matchId: number): Promise<MatchDetail> {
  const response = await fetch(`/api/matches/${matchId}`)
  if (!response.ok) throw new Error(`GET match detail failed: ${response.status}`)
  return response.json()
}

export function useMatchDetail(matchId: number) {
  return useQuery({
    queryKey: ['matches', matchId],
    queryFn: () => fetchMatchDetail(matchId),
  })
}
