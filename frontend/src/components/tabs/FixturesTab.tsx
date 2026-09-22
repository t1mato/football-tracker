import { useState } from 'react'
import { useLeagueFixtures } from '../../hooks/useLeagueMatches'
import { MatchDetailPanel } from '../MatchDetailPanel'
import { ErrorMessage } from '../ErrorMessage'
import { FixtureCard } from '../FixtureCard'

interface FixturesTabProps {
  competitionCode: string
  seasonId: number | undefined
  active: boolean
}

export function FixturesTab({ competitionCode, seasonId, active }: FixturesTabProps) {
  const { data, isLoading, error } = useLeagueFixtures(competitionCode, seasonId, active)
  const [expandedMatchId, setExpandedMatchId] = useState<number | null>(null)

  if (!active) return null
  if (isLoading) return <p>Loading...</p>
  if (error) return <ErrorMessage resource="fixtures" />
  if (!data || data.length === 0) return <p>No upcoming fixtures scheduled.</p>

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
          status={match.status}
          onClick={() =>
            setExpandedMatchId(expandedMatchId === match.match_id ? null : match.match_id)
          }
        >
          {expandedMatchId === match.match_id && <MatchDetailPanel matchId={match.match_id} />}
        </FixtureCard>
      ))}
    </div>
  )
}
