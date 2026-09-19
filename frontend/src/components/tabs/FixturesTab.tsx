import { useState } from 'react'
import { useLeagueFixtures } from '../../hooks/useLeagueMatches'
import { MatchDetailPanel } from '../MatchDetailPanel'

interface FixturesTabProps {
  competitionCode: string
  seasonId: number | undefined
  active: boolean
}

export function FixturesTab({ competitionCode, seasonId, active }: FixturesTabProps) {
  const { data, isLoading } = useLeagueFixtures(competitionCode, seasonId, active)
  const [expandedMatchId, setExpandedMatchId] = useState<number | null>(null)

  if (!active) return null
  if (isLoading) return <p>Loading...</p>
  if (!data || data.length === 0) return <p>No upcoming fixtures scheduled.</p>

  return (
    <div>
      <table className="w-full text-sm">
        <tbody>
          {data.map((match) => (
            <tr
              key={match.match_id}
              className="border-t border-line cursor-pointer"
              onClick={() =>
                setExpandedMatchId(expandedMatchId === match.match_id ? null : match.match_id)
              }
            >
              <td className="py-1.5">{match.home_team_name}</td>
              <td className="text-center">{new Date(match.kickoff_utc).toLocaleString()}</td>
              <td>{match.away_team_name}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {expandedMatchId !== null && <MatchDetailPanel matchId={expandedMatchId} />}
    </div>
  )
}
