import { useTeamUpcoming } from '../../hooks/useTeamMatches'
import { formatKickoff } from '../../lib/formatKickoff'
import { ErrorMessage } from '../ErrorMessage'

interface TeamFixturesTabProps {
  teamId: number | null
  active: boolean
}

export function TeamFixturesTab({ teamId, active }: TeamFixturesTabProps) {
  const { data, isLoading, error } = useTeamUpcoming(teamId, active)

  if (!active) return null
  if (isLoading) return <p>Loading...</p>
  if (error) return <ErrorMessage resource="upcoming fixtures" />
  if (!data || data.length === 0) return <p>No upcoming fixtures scheduled.</p>

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-text-muted text-xs uppercase">
          <th>Kickoff (UTC)</th>
          <th>Opponent</th>
          <th>Competition</th>
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
          </tr>
        ))}
      </tbody>
    </table>
  )
}
