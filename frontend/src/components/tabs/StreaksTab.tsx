import { useLeagueStreaks, useTeamsInSeason } from '../../hooks/useLeagueStreaks'

interface StreaksTabProps {
  competitionCode: string
  currentSeasonId: number | undefined
  active: boolean
}

export function StreaksTab({ competitionCode, currentSeasonId, active }: StreaksTabProps) {
  const { data: streaks, isLoading } = useLeagueStreaks(competitionCode, active)
  const { data: currentTeams } = useTeamsInSeason(competitionCode, currentSeasonId, active)

  if (!active) return null
  if (isLoading) return <p>Loading...</p>
  if (!streaks || streaks.length === 0) return <p>No streak data available for this competition.</p>

  const currentTeamIds = new Set((currentTeams ?? []).map((t) => t.team_id))
  const current = streaks
    .filter((s) => currentTeamIds.has(s.team_id))
    .sort((a, b) => b.current_win_streak - a.current_win_streak)

  return (
    <div>
      <h3 className="font-semibold">Current Streaks</h3>
      <table className="w-full text-sm mb-4">
        <tbody>
          {current.map((row) => (
            <tr key={row.team_id} className="border-t border-line">
              <td className="py-1.5">{row.team_name}</td>
              <td className="text-center">{row.current_win_streak}W</td>
              <td className="text-center">{row.current_unbeaten_streak} unbeaten</td>
            </tr>
          ))}
        </tbody>
      </table>
      <h3 className="font-semibold">All-Time Records</h3>
      <table className="w-full text-sm">
        <tbody>
          {[...streaks]
            .sort((a, b) => b.longest_win_streak - a.longest_win_streak)
            .map((row) => (
              <tr key={row.team_id} className="border-t border-line">
                <td className="py-1.5">{row.team_name}</td>
                <td className="text-center">{row.longest_win_streak}W</td>
                <td className="text-center">{row.longest_unbeaten_streak} unbeaten</td>
              </tr>
            ))}
        </tbody>
      </table>
    </div>
  )
}
