import { useState } from 'react'
import { useCompetitions } from '../hooks/useCompetitions'
import { useCurrentSeason } from '../hooks/useLeagueSeasons'
import { useTeams } from '../hooks/useTeams'
import { TeamCard } from '../components/TeamCard'
import { TeamDetailDialog } from '../components/TeamDetailDialog'

export function Teams() {
  const { data: competitions, isLoading, error } = useCompetitions()
  const [selectedCode, setSelectedCode] = useState('')
  const code = selectedCode || competitions?.[0]?.competition_code || ''

  const { data: seasonId } = useCurrentSeason(code, code !== '')
  const {
    data: teams,
    isLoading: teamsLoading,
    error: teamsError,
  } = useTeams(code, seasonId, code !== '' && seasonId !== undefined)
  const [openTeamId, setOpenTeamId] = useState<number | null>(null)

  if (isLoading) return <p>Loading...</p>
  if (error) return <p>Error: {error.message}</p>

  return (
    <div className="p-6">
      <h1 className="font-display text-4xl uppercase mb-6">Teams</h1>
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
      {teamsLoading && <p>Loading...</p>}
      {teamsError && <p>Error: {teamsError.message}</p>}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {teams?.map((t) => (
          <TeamCard key={t.team_id} team={t} onView={() => setOpenTeamId(t.team_id)} />
        ))}
      </div>
      <TeamDetailDialog
        teamId={openTeamId}
        teamName={teams?.find((t) => t.team_id === openTeamId)?.team_name}
        leagueCode={code}
        leagueSeasonId={seasonId}
        onClose={() => setOpenTeamId(null)}
      />
    </div>
  )
}
