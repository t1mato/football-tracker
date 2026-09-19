import { useState } from 'react'
import { useLeagueFixtures } from '../../hooks/useLeagueMatches'
import { MatchDetailPanel } from '../MatchDetailPanel'
import { ErrorMessage } from '../ErrorMessage'
import { formatKickoff } from '../../lib/formatKickoff'

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
              <td className="py-1.5 flex items-center gap-2">
                {match.home_crest && (
                  <img src={match.home_crest} alt="" className="w-5 h-5 object-contain" />
                )}
                {match.home_team_name}
              </td>
              <td className="text-center">
                {formatKickoff(match.kickoff_utc, match.kickoff_time_confirmed)}
              </td>
              <td className="flex items-center gap-2">
                {match.away_crest && (
                  <img src={match.away_crest} alt="" className="w-5 h-5 object-contain" />
                )}
                {match.away_team_name}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {expandedMatchId !== null && <MatchDetailPanel matchId={expandedMatchId} />}
    </div>
  )
}
