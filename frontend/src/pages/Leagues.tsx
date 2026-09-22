import { useState } from 'react'
import { useCompetitions } from '../hooks/useCompetitions'
import { LeagueCard } from '../components/LeagueCard'
import { LeagueDetailDialog } from '../components/LeagueDetailDialog'
import { CrossLeagueDashboard } from '../components/CrossLeagueDashboard'
import { Frame } from '../components/Frame'

export function Leagues() {
  const { data, isLoading, error } = useCompetitions()
  const [openCode, setOpenCode] = useState<string | null>(null)
  const openCompetition = data?.find((c) => c.competition_code === openCode)

  if (isLoading) return <p>Loading...</p>
  if (error) return <p>Error: {error.message}</p>

  return (
    <div className="flex flex-col gap-14">
      <div>
        <h1 className="font-display text-5xl uppercase mb-8">Leagues</h1>
        <Frame className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data?.map((c) => (
            <LeagueCard
              key={c.competition_code}
              competition={c}
              selected={c.competition_code === openCode}
              onView={() => setOpenCode(c.competition_code)}
            />
          ))}
        </Frame>
      </div>
      <LeagueDetailDialog
        competitionCode={openCode}
        competitionName={openCompetition?.competition_name}
        competitionEmblem={openCompetition?.emblem}
        onClose={() => setOpenCode(null)}
      />
      <div>
        <h2 className="font-display text-3xl uppercase mb-4">Cross-League Dashboard</h2>
        <CrossLeagueDashboard />
      </div>
    </div>
  )
}
