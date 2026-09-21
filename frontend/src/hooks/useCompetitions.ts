import { useQuery } from '@tanstack/react-query'

export interface Competition {
  competition_code: string
  competition_name: string
  area_name: string
  emblem: string | null
  area_flag: string | null
}

async function fetchCompetitions(): Promise<Competition[]> {
  const response = await fetch('/api/competitions')
  if (!response.ok) {
    throw new Error(`GET /api/competitions failed: ${response.status}`)
  }
  return response.json()
}

export function useCompetitions(enabled = true) {
  return useQuery({
    queryKey: ['competitions'],
    queryFn: fetchCompetitions,
    enabled,
  })
}
