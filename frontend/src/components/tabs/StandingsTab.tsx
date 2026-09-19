import { useReconstructedStandings, useStandings } from '../../hooks/useStandings'
import { ErrorMessage } from '../ErrorMessage'

interface StandingsTabProps {
  competitionCode: string
  seasonId: number | undefined
  isCurrentSeason: boolean
  active: boolean
}

export function StandingsTab({
  competitionCode,
  seasonId,
  isCurrentSeason,
  active,
}: StandingsTabProps) {
  const current = useStandings(competitionCode, seasonId, active && isCurrentSeason)
  const reconstructed = useReconstructedStandings(
    competitionCode,
    seasonId,
    active && !isCurrentSeason
  )

  if (!active) return null

  if (isCurrentSeason) {
    if (current.isLoading) return <p>Loading...</p>
    if (current.error) return <ErrorMessage resource="standings" />
    if (!current.data || current.data.table === null) {
      return <p>{current.data?.message ?? 'No standings available yet for this competition.'}</p>
    }
    return (
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-text-muted text-xs uppercase">
            <th>#</th>
            <th>Team</th>
            <th className="text-center">P</th>
            <th className="text-center">W</th>
            <th className="text-center">D</th>
            <th className="text-center">L</th>
            <th className="text-center">GD</th>
            <th className="text-center">Pts</th>
          </tr>
        </thead>
        <tbody>
          {current.data.table.map((row) => (
            <tr key={row.team_id} className="border-t border-line">
              <td>{row.position}</td>
              <td className="flex items-center gap-2 py-1.5">
                {row.crest && <img src={row.crest} alt="" className="w-5 h-5 object-contain" />}
                {row.team_name}
              </td>
              <td className="text-center">{row.played_games}</td>
              <td className="text-center">{row.won}</td>
              <td className="text-center">{row.draw}</td>
              <td className="text-center">{row.lost}</td>
              <td
                className={`text-center font-semibold ${row.goal_difference > 0 ? 'text-green' : row.goal_difference < 0 ? 'text-red' : ''}`}
              >
                {row.goal_difference}
              </td>
              <td className="text-center font-semibold">{row.points}</td>
            </tr>
          ))}
        </tbody>
      </table>
    )
  }

  if (reconstructed.isLoading) return <p>Loading...</p>
  if (reconstructed.error) return <ErrorMessage resource="standings" />
  if (!reconstructed.data || reconstructed.data.length === 0) {
    return <p>No reconstructed final table available for this season.</p>
  }
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-text-muted text-xs uppercase">
          <th>#</th>
          <th>Team</th>
          <th className="text-center">Pts</th>
          <th className="text-center">GD</th>
          <th className="text-center">GF</th>
        </tr>
      </thead>
      <tbody>
        {reconstructed.data.map((row) => (
          <tr key={`${row.group_name ?? ''}-${row.position}`} className="border-t border-line">
            <td>{row.position}</td>
            <td className="py-1.5">{row.team_name}</td>
            <td className="text-center font-semibold">{row.points}</td>
            <td className="text-center">{row.goal_difference}</td>
            <td className="text-center">{row.goals_for}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
