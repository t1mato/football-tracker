import { useQuery } from '@tanstack/react-query'

export interface PlayerRow {
  player_id: number
  player_name: string
  position: string | null
  nationality: string | null
  team_name: string | null
  crest: string | null
}

async function fetchPlayersDirectory(): Promise<PlayerRow[]> {
  const response = await fetch('/api/players')
  if (!response.ok) throw new Error(`GET players failed: ${response.status}`)
  return response.json()
}

export function usePlayersDirectory() {
  return useQuery({
    queryKey: ['players', 'directory'],
    queryFn: fetchPlayersDirectory,
  })
}
