import { useQuery } from '@tanstack/react-query'

interface Competition {
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

export function Leagues() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['competitions'],
    queryFn: fetchCompetitions,
  })

  if (isLoading) return <p>Loading...</p>
  if (error) return <p>Error: {error.message}</p>

  return (
    <div>
      <h1 className="font-display text-4xl">Leagues</h1>
      <ul>
        {data?.map((c) => (
          <li key={c.competition_code}>{c.competition_name} — {c.area_name}</li>
        ))}
      </ul>
    </div>
  )
}
