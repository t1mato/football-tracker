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

export interface PlayerBio {
  player_name: string
  position: string | null
  nationality: string | null
  date_of_birth: string | null
  team_name: string | null
  crest: string | null
}

async function fetchPlayerBio(playerId: number): Promise<PlayerBio> {
  const response = await fetch(`/api/players/${playerId}`)
  if (response.status === 404) throw new Error('Player not found')
  if (!response.ok) throw new Error(`GET player bio failed: ${response.status}`)
  return response.json()
}

export function usePlayerBio(playerId: number | null, enabled: boolean) {
  return useQuery({
    queryKey: ['players', playerId, 'bio'],
    queryFn: () => fetchPlayerBio(playerId as number),
    enabled: enabled && playerId !== null,
  })
}

export interface ScoringHistoryRow {
  competition_name: string
  start_date: string
  end_date: string
  goals: number
  assists: number
  played_matches: number
  penalties: number
}

async function fetchScoringHistory(playerId: number): Promise<ScoringHistoryRow[]> {
  const response = await fetch(`/api/players/${playerId}/scoring-history`)
  if (!response.ok) throw new Error(`GET scoring history failed: ${response.status}`)
  return response.json()
}

export function usePlayerScoringHistory(playerId: number | null, enabled: boolean) {
  return useQuery({
    queryKey: ['players', playerId, 'scoring-history'],
    queryFn: () => fetchScoringHistory(playerId as number),
    enabled: enabled && playerId !== null,
  })
}
