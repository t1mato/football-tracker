import { useTeamForm } from '../../hooks/useTeamMatches'
import { formatKickoff } from '../../lib/formatKickoff'
import { formatScore } from '../../lib/formatScore'
import { ErrorMessage } from '../ErrorMessage'
import { ResultBadge } from '../ResultBadge'

interface FormTabProps {
  teamId: number | null
  active: boolean
}

export function FormTab({ teamId, active }: FormTabProps) {
  const { data, isLoading, error } = useTeamForm(teamId, active)

  if (!active) return null
  if (isLoading) return <p>Loading...</p>
  if (error) return <ErrorMessage resource="recent form" />
  if (!data || data.length === 0) return <p>No finished matches recorded yet.</p>

  return (
    <div>
      <p className="text-lg text-text-muted mb-2">Across all competitions</p>
      <table className="w-full text-lg">
        <thead>
          <tr className="text-left text-text-muted text-base uppercase">
            <th className="pb-3">Kickoff (UTC)</th>
            <th className="pb-3">Opponent</th>
            <th className="pb-3">Competition</th>
            <th className="pb-3 text-center">Score</th>
            <th className="pb-3 text-center">Result</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr
              key={`${row.kickoff_utc}-${row.opponent_team_name}`}
              className="border-t border-line"
            >
              <td>{formatKickoff(row.kickoff_utc, row.kickoff_time_confirmed)}</td>
              <td className="flex items-center gap-2.5 py-3">
                {row.opponent_crest && (
                  <img src={row.opponent_crest} alt="" className="w-6 h-6 object-contain" />
                )}
                {row.opponent_team_name}
              </td>
              <td>{row.competition_name}</td>
              <td className="text-center">{formatScore(row.goals_for, row.goals_against)}</td>
              <td className="text-center">
                <ResultBadge result={row.result} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
