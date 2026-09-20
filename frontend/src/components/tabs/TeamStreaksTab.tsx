import { useTeamStreaks } from '../../hooks/useTeamStreaks'
import { ErrorMessage } from '../ErrorMessage'

interface TeamStreaksTabProps {
  teamId: number | null
  leagueCode: string
  active: boolean
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-line p-3 text-center">
      <p className="text-xs uppercase text-text-muted">{label}</p>
      <p className="text-xl font-semibold">{value}</p>
    </div>
  )
}

export function TeamStreaksTab({ teamId, leagueCode, active }: TeamStreaksTabProps) {
  const { data, isLoading, error } = useTeamStreaks(teamId, leagueCode, active)

  if (!active) return null
  if (isLoading) return <p>Loading...</p>
  if (error) return <ErrorMessage resource="streaks" />
  if (!data || data.streaks === null) {
    return <p>{data?.message ?? 'No streak data available for this team in this league yet.'}</p>
  }

  const s = data.streaks
  return (
    <div>
      <p className="text-sm text-text-muted mb-2">In this league only</p>
      <div className="grid grid-cols-2 gap-3">
        <Stat label="Current win streak" value={s.current_win_streak} />
        <Stat label="Current unbeaten streak" value={s.current_unbeaten_streak} />
        <Stat label="Longest win streak" value={s.longest_win_streak} />
        <Stat label="Longest unbeaten streak" value={s.longest_unbeaten_streak} />
      </div>
    </div>
  )
}
