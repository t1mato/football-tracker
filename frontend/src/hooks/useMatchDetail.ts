import { useQuery } from '@tanstack/react-query'

export interface MatchDetail {
  match_id: number
  venue_display_name: string | null
  venue_needs_review: boolean
  capacity: number | null
  latitude: number | null
  longitude: number | null
  temperature_2m: number | null
  precipitation: number | null
  wind_speed_10m: number | null
  weather_data_type: string | null
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
