import { useCrossLeagueStats } from '../hooks/useCrossLeagueStats'
import { ErrorMessage } from './ErrorMessage'

export function CrossLeagueDashboard() {
  const { data, isLoading, error } = useCrossLeagueStats()

  if (isLoading) return <p>Loading...</p>
  if (error) return <ErrorMessage resource="cross-league stats" />
  if (!data) return null

  return (
    <div className="mt-8">
      <h2 className="font-display text-2xl uppercase mb-3">Cross-League Dashboard</h2>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-text-muted text-xs uppercase">
            <th>Competition</th>
            <th className="text-center">Decided Matches</th>
            <th className="text-center">Avg Goals/Match</th>
            <th className="text-center">Avg Margin</th>
            <th className="text-center">Home Win %</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr key={row.competition_name} className="border-t border-line">
              <td className="py-1.5">{row.competition_name}</td>
              <td className="text-center">{row.decided_matches ?? '—'}</td>
              <td className="text-center">{row.avg_goals_per_match?.toFixed(2) ?? '—'}</td>
              <td className="text-center">{row.avg_goal_margin?.toFixed(2) ?? '—'}</td>
              <td className="text-center">
                {row.home_win_rate !== null ? `${(row.home_win_rate * 100).toFixed(0)}%` : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
