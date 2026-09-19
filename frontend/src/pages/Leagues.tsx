import { useState } from 'react'
import { useCompetitions } from '../hooks/useCompetitions'
import { LeagueCard } from '../components/LeagueCard'
import { LeagueDetailDialog } from '../components/LeagueDetailDialog'

export function Leagues() {
  const { data, isLoading, error } = useCompetitions()
  const [openCode, setOpenCode] = useState<string | null>(null)

  if (isLoading) return <p>Loading...</p>
  if (error) return <p>Error: {error.message}</p>

  return (
    <div className="p-6">
      <h1 className="font-display text-4xl uppercase mb-6">Leagues</h1>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {data?.map((c) => (
          <LeagueCard
            key={c.competition_code}
            competition={c}
            onView={() => setOpenCode(c.competition_code)}
          />
        ))}
      </div>
      <LeagueDetailDialog
        competitionCode={openCode}
        competitionName={data?.find((c) => c.competition_code === openCode)?.competition_name}
        onClose={() => setOpenCode(null)}
      />
    </div>
  )
}
