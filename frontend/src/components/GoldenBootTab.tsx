import { useState } from 'react'
import { useCompetitions } from '../hooks/useCompetitions'
import { useCurrentSeason } from '../hooks/useLeagueSeasons'
import { LeadersTab } from './tabs/LeadersTab'

interface GoldenBootTabProps {
  active: boolean
}

export function GoldenBootTab({ active }: GoldenBootTabProps) {
  const { data: competitions, isLoading, error } = useCompetitions(active)
  const [selectedCode, setSelectedCode] = useState('')
  const code = selectedCode || competitions?.[0]?.competition_code || ''
  const { data: seasonId } = useCurrentSeason(code, active && code !== '')

  if (!active) return null
  if (isLoading) return <p>Loading...</p>
  if (error) return <p>Error: {error.message}</p>

  return (
    <div>
      <select
        value={code}
        onChange={(e) => setSelectedCode(e.target.value)}
        className="mb-4 rounded border border-line px-2 py-1"
      >
        {competitions?.map((c) => (
          <option key={c.competition_code} value={c.competition_code}>
            {c.competition_name}
          </option>
        ))}
      </select>
      <LeadersTab competitionCode={code} seasonId={seasonId} active={active} />
    </div>
  )
}
