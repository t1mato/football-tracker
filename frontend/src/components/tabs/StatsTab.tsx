import { useTeamStats } from '../../hooks/useTeamStats'
import { ErrorMessage } from '../ErrorMessage'

interface StatsTabProps {
  teamId: number | null
  leagueCode: string
  leagueSeasonId: number | undefined
  active: boolean
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-line p-3 text-center">
      <p className="text-xs uppercase text-text-muted">{label}</p>
      <p className="text-xl font-semibold">{value}</p>
    </div>
  )
}

export function StatsTab({ teamId, leagueCode, leagueSeasonId, active }: StatsTabProps) {
  const { data, isLoading, error } = useTeamStats(teamId, leagueCode, leagueSeasonId, active)

  if (!active) return null
  if (isLoading) return <p>Loading...</p>
  if (error) return <ErrorMessage resource="stats" />
  if (!data || data.stats === null) {
    return <p>{data?.message ?? 'No season stats available for this team in this league yet.'}</p>
  }

  const s = data.stats
  return (
    <div className="grid grid-cols-4 gap-3">
      <Stat label="Position" value={s.position} />
      <Stat label="Played" value={s.played_games} />
      <Stat label="Points" value={s.points} />
      <Stat label="GD" value={s.goal_difference} />
      <Stat label="Won" value={s.won} />
      <Stat label="Drawn" value={s.draw} />
      <Stat label="Lost" value={s.lost} />
      <Stat label="GF-GA" value={`${s.goals_for}-${s.goals_against}`} />
    </div>
  )
}
