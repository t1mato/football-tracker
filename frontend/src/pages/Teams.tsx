import { useState } from 'react'
import { useCompetitions } from '../hooks/useCompetitions'
import { useCurrentSeason } from '../hooks/useLeagueSeasons'
import { useTeams } from '../hooks/useTeams'
import { TeamCard } from '../components/TeamCard'
import { TeamDetailDialog } from '../components/TeamDetailDialog'
import { Frame } from '../components/Frame'

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
    <div>
      <h1 className="font-display text-5xl uppercase mb-8">Clubs</h1>
      <Frame>
        <select
          value={code}
          onChange={(e) => setSelectedCode(e.target.value)}
          className="mb-6 rounded-full bg-violet-soft text-violet font-bold text-lg px-5 py-2 border-none"
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
            <TeamCard
              key={t.team_id}
              team={t}
              selected={t.team_id === openTeamId}
              onView={() => setOpenTeamId(t.team_id)}
            />
          ))}
        </div>
      </Frame>
      <TeamDetailDialog
        teamId={openTeamId}
        teamName={teams?.find((t) => t.team_id === openTeamId)?.team_name}
        teamCrest={teams?.find((t) => t.team_id === openTeamId)?.crest}
        leagueCode={code}
        leagueSeasonId={seasonId}
        onClose={() => setOpenTeamId(null)}
      />
    </div>
  )
}
