import { useTeamUpcoming } from '../../hooks/useTeamMatches'
import { ErrorMessage } from '../ErrorMessage'
import { FixtureCard } from '../FixtureCard'

interface TeamFixturesTabProps {
  teamId: number | null
  teamName?: string
  teamCrest?: string | null
  active: boolean
}

export function TeamFixturesTab({ teamId, teamName, teamCrest, active }: TeamFixturesTabProps) {
  const { data, isLoading, error } = useTeamUpcoming(teamId, active)

  if (!active) return null
  if (isLoading) return <p>Loading...</p>
  if (error) return <ErrorMessage resource="upcoming fixtures" />
  if (!data || data.length === 0) return <p>No upcoming fixtures scheduled.</p>

  return (
    <div className="flex flex-col gap-4">
      {data.map((row) => (
        <FixtureCard
          key={`${row.kickoff_utc}-${row.opponent_team_name}`}
          homeTeamName={teamName ?? 'This club'}
          homeCrest={teamCrest ?? null}
          awayTeamName={row.opponent_team_name}
          awayCrest={row.opponent_crest}
          kickoffUtc={row.kickoff_utc}
          kickoffTimeConfirmed={row.kickoff_time_confirmed}
          status={row.status}
          competitionName={row.competition_name}
          competitionEmblem={row.competition_emblem}
        />
      ))}
    </div>
  )
}
