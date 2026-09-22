import { useCrossLeagueStats } from '../hooks/useCrossLeagueStats'
import { ErrorMessage } from './ErrorMessage'
import { Frame } from './Frame'

export function CrossLeagueDashboard() {
  const { data, isLoading, error } = useCrossLeagueStats()

  if (isLoading) return <p>Loading...</p>
  if (error) return <ErrorMessage resource="cross-league stats" />
  if (!data) return null

  return (
    <Frame>
      <table className="w-full text-lg">
        <thead>
          <tr className="text-left text-text-muted text-base uppercase">
            <th className="pb-3">Competition</th>
            <th className="pb-3 text-center">Decided Matches</th>
            <th className="pb-3 text-center">Avg Goals/Match</th>
            <th className="pb-3 text-center">Avg Margin</th>
            <th className="pb-3 text-center">Home Win %</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr key={row.competition_name} className="border-t border-line">
              <td className="py-3">{row.competition_name}</td>
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
    </Frame>
  )
}
