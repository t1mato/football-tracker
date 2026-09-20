import { useTeamForm } from '../../hooks/useTeamMatches'
import { formatKickoff } from '../../lib/formatKickoff'
import { formatScore } from '../../lib/formatScore'
import { ErrorMessage } from '../ErrorMessage'

interface FormTabProps {
  teamId: number | null
  active: boolean
}

function resultColor(result: string | null): string {
  if (result === 'W') return 'text-green'
  if (result === 'L') return 'text-red'
  if (result === 'D') return 'text-yellow'
  return ''
}

export function FormTab({ teamId, active }: FormTabProps) {
  const { data, isLoading, error } = useTeamForm(teamId, active)

  if (!active) return null
  if (isLoading) return <p>Loading...</p>
  if (error) return <ErrorMessage resource="recent form" />
  if (!data || data.length === 0) return <p>No finished matches recorded yet.</p>

  return (
    <div>
      <p className="text-sm text-text-muted mb-2">Across all competitions</p>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-text-muted text-xs uppercase">
            <th>Kickoff (UTC)</th>
            <th>Opponent</th>
            <th>Competition</th>
            <th className="text-center">Score</th>
            <th className="text-center">Result</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr
              key={`${row.kickoff_utc}-${row.opponent_team_name}`}
              className="border-t border-line"
            >
              <td>{formatKickoff(row.kickoff_utc, row.kickoff_time_confirmed)}</td>
              <td className="flex items-center gap-2 py-1.5">
                {row.opponent_crest && (
                  <img src={row.opponent_crest} alt="" className="w-5 h-5 object-contain" />
                )}
                {row.opponent_team_name}
              </td>
              <td>{row.competition_name}</td>
              <td className="text-center">{formatScore(row.goals_for, row.goals_against)}</td>
              <td className={`text-center font-semibold ${resultColor(row.result)}`}>
                {row.result}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
