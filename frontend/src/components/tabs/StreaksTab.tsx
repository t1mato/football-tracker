import { useLeagueStreaks, useTeamsInSeason } from '../../hooks/useLeagueStreaks'
import { ErrorMessage } from '../ErrorMessage'

interface StreaksTabProps {
  competitionCode: string
  currentSeasonId: number | undefined
  active: boolean
}

export function StreaksTab({ competitionCode, currentSeasonId, active }: StreaksTabProps) {
  const { data: streaks, isLoading, error } = useLeagueStreaks(competitionCode, active)
  const {
    data: currentTeams,
    isLoading: teamsLoading,
    error: teamsError,
  } = useTeamsInSeason(competitionCode, currentSeasonId, active)

  if (!active) return null
  if (isLoading || teamsLoading) return <p>Loading...</p>
  if (error || teamsError) return <ErrorMessage resource="streaks" />
  if (!streaks || streaks.length === 0) return <p>No streak data available for this competition.</p>

  const currentTeamIds = new Set((currentTeams ?? []).map((t) => t.team_id))
  const current = streaks
    .filter((s) => currentTeamIds.has(s.team_id))
    .sort(
      (a, b) =>
        b.current_win_streak - a.current_win_streak ||
        b.current_unbeaten_streak - a.current_unbeaten_streak ||
        a.team_name.localeCompare(b.team_name)
    )
    .slice(0, 5)

  const longest = [...streaks]
    .sort(
      (a, b) =>
        b.longest_win_streak - a.longest_win_streak ||
        b.longest_unbeaten_streak - a.longest_unbeaten_streak ||
        a.team_name.localeCompare(b.team_name)
    )
    .slice(0, 5)

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h3 className="font-bold mb-2">Current Streaks</h3>
        <table className="w-full text-lg">
          <tbody>
            {current.map((row) => (
              <tr key={row.team_id} className="border-t border-line">
                <td className="py-3">{row.team_name}</td>
                <td className="text-center">{row.current_win_streak}W</td>
                <td className="text-center">{row.current_unbeaten_streak} unbeaten</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div>
        <h3 className="font-bold mb-2">All-Time Records</h3>
        <table className="w-full text-lg">
          <tbody>
            {longest.map((row) => (
              <tr key={row.team_id} className="border-t border-line">
                <td className="py-3">{row.team_name}</td>
                <td className="text-center">{row.longest_win_streak}W</td>
                <td className="text-center">{row.longest_unbeaten_streak} unbeaten</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
