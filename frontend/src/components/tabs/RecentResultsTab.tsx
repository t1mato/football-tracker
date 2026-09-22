import { useState } from 'react'
import { useLeagueResults } from '../../hooks/useLeagueMatches'
import { MatchDetailPanel } from '../MatchDetailPanel'
import { ErrorMessage } from '../ErrorMessage'
import { FixtureCard } from '../FixtureCard'

interface RecentResultsTabProps {
  competitionCode: string
  seasonId: number | undefined
  active: boolean
}

export function RecentResultsTab({ competitionCode, seasonId, active }: RecentResultsTabProps) {
  const { data, isLoading, error } = useLeagueResults(competitionCode, seasonId, active)
  const [expandedMatchId, setExpandedMatchId] = useState<number | null>(null)

  if (!active) return null
  if (isLoading) return <p>Loading...</p>
  if (error) return <ErrorMessage resource="results" />
  if (!data || data.length === 0) return <p>No results yet this season.</p>

  return (
    <div className="flex flex-col gap-4">
      {data.map((match) => (
        <FixtureCard
          key={match.match_id}
          homeTeamName={match.home_team_name}
          homeCrest={match.home_crest}
          awayTeamName={match.away_team_name}
          awayCrest={match.away_crest}
          kickoffUtc={match.kickoff_utc}
          kickoffTimeConfirmed={match.kickoff_time_confirmed}
          fullTimeHome={match.full_time_home ?? null}
          fullTimeAway={match.full_time_away ?? null}
          onClick={() =>
            setExpandedMatchId(expandedMatchId === match.match_id ? null : match.match_id)
          }
        />
      ))}
      {expandedMatchId !== null && <MatchDetailPanel matchId={expandedMatchId} />}
    </div>
  )
}
