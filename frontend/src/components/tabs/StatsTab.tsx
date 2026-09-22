import {
  useTeamAssists,
  useTeamScorers,
  useTeamStats,
  type TeamAssistRow,
  type TeamScorerRow,
} from '../../hooks/useTeamStats'
import { ErrorMessage } from '../ErrorMessage'

interface StatsTabProps {
  teamId: number | null
  leagueCode: string
  leagueSeasonId: number | undefined
  active: boolean
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg bg-surface-2 p-4 flex flex-col gap-1">
      <p className="font-display text-3xl leading-none">{value}</p>
      <p className="text-sm uppercase tracking-wide text-text-muted">{label}</p>
    </div>
  )
}

function ScorersList({ rows }: { rows: TeamScorerRow[] }) {
  if (rows.length === 0) return <p className="text-text-muted">No scorers recorded yet.</p>
  return (
    <table className="w-full text-lg">
      <thead>
        <tr className="text-left text-text-muted text-base uppercase">
          <th className="pb-3 px-2">Player</th>
          <th className="pb-3 px-2 text-center">P</th>
          <th className="pb-3 px-2 text-center">G</th>
          <th className="pb-3 px-2 text-center">Pen</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.player_name} className="border-t border-line">
            <td className="flex items-center gap-2.5 py-3 px-2">
              {row.crest && <img src={row.crest} alt="" className="w-6 h-6 object-contain" />}
              {row.player_name}
            </td>
            <td className="px-2 text-center">{row.played_matches}</td>
            <td className="px-2 text-center">{row.goals}</td>
            <td className="px-2 text-center">{row.penalties}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function AssistsList({ rows }: { rows: TeamAssistRow[] }) {
  if (rows.length === 0) return <p className="text-text-muted">No assists recorded yet.</p>
  return (
    <table className="w-full text-lg">
      <thead>
        <tr className="text-left text-text-muted text-base uppercase">
          <th className="pb-3 px-2">Player</th>
          <th className="pb-3 px-2 text-center">P</th>
          <th className="pb-3 px-2 text-center">A</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.player_name} className="border-t border-line">
            <td className="flex items-center gap-2.5 py-3 px-2">
              {row.crest && <img src={row.crest} alt="" className="w-6 h-6 object-contain" />}
              {row.player_name}
            </td>
            <td className="px-2 text-center">{row.played_matches}</td>
            <td className="px-2 text-center">{row.assists}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export function StatsTab({ teamId, leagueCode, leagueSeasonId, active }: StatsTabProps) {
  const { data, isLoading, error } = useTeamStats(teamId, leagueCode, leagueSeasonId, active)
  const { data: scorers, error: scorersError } = useTeamScorers(
    teamId,
    leagueCode,
    leagueSeasonId,
    active
  )
  const { data: assists, error: assistsError } = useTeamAssists(
    teamId,
    leagueCode,
    leagueSeasonId,
    active
  )

  if (!active) return null
  if (isLoading) return <p>Loading...</p>
  if (error) return <ErrorMessage resource="stats" />
  if (!data || data.stats === null) {
    return <p>{data?.message ?? 'No season stats available for this team in this league yet.'}</p>
  }

  const s = data.stats
  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-4 gap-4">
        <Stat label="Position" value={s.position} />
        <Stat label="Played" value={s.played_games} />
        <Stat label="Points" value={s.points} />
        <Stat label="GD" value={s.goal_difference} />
        <Stat label="Won" value={s.won} />
        <Stat label="Drawn" value={s.draw} />
        <Stat label="Lost" value={s.lost} />
        <Stat label="GF-GA" value={`${s.goals_for}-${s.goals_against}`} />
      </div>
      <div className="rounded-2xl border border-line bg-surface shadow-card p-5">
        <h3 className="font-bold text-xl mb-3">Top Scorers</h3>
        {scorersError ? <ErrorMessage resource="top scorers" /> : <ScorersList rows={scorers ?? []} />}
      </div>
      <div className="rounded-2xl border border-line bg-surface shadow-card p-5">
        <h3 className="font-bold text-xl mb-3">Top Assists</h3>
        {assistsError ? <ErrorMessage resource="top assists" /> : <AssistsList rows={assists ?? []} />}
      </div>
    </div>
  )
}
