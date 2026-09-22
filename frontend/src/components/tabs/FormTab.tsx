import { useTeamForm } from '../../hooks/useTeamMatches'
import { ErrorMessage } from '../ErrorMessage'
import { FixtureCard } from '../FixtureCard'

interface FormTabProps {
  teamId: number | null
  teamName?: string
  teamCrest?: string | null
  active: boolean
}

export function FormTab({ teamId, teamName, teamCrest, active }: FormTabProps) {
  const { data, isLoading, error } = useTeamForm(teamId, active)

  if (!active) return null
  if (isLoading) return <p>Loading...</p>
  if (error) return <ErrorMessage resource="recent form" />
  if (!data || data.length === 0) return <p>No finished matches recorded yet.</p>

  return (
    <div>
      <p className="text-lg text-text-muted mb-4">Across all competitions</p>
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
            fullTimeHome={row.goals_for}
            fullTimeAway={row.goals_against}
            result={row.result}
            competitionName={row.competition_name}
            competitionEmblem={row.competition_emblem}
          />
        ))}
      </div>
    </div>
  )
}
