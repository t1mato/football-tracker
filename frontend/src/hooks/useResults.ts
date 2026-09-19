import { useQuery } from '@tanstack/react-query'

// Minimal shape for now -- Task 7 owns the full Recent Results tab and
// defines the real response type against the actual `/results` payload.
export type ResultRow = Record<string, unknown>

async function fetchResults(code: string, season: number): Promise<ResultRow[]> {
  const response = await fetch(`/api/leagues/${code}/results?season=${season}`)
  if (!response.ok) throw new Error(`GET results failed: ${response.status}`)
  return response.json()
}

export function useResults(code: string, season: number | undefined, enabled: boolean) {
  return useQuery({
    queryKey: ['leagues', code, 'results', season],
    queryFn: () => fetchResults(code, season as number),
    enabled: enabled && season !== undefined,
  })
}
