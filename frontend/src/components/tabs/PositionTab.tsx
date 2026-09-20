import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useTeamPositionHistory } from '../../hooks/useTeamStats'
import { ErrorMessage } from '../ErrorMessage'

interface PositionTabProps {
  teamId: number | null
  leagueCode: string
  leagueSeasonId: number | undefined
  active: boolean
}

export function PositionTab({ teamId, leagueCode, leagueSeasonId, active }: PositionTabProps) {
  const { data, isLoading, error } = useTeamPositionHistory(
    teamId,
    leagueCode,
    leagueSeasonId,
    active
  )

  if (!active) return null
  if (isLoading) return <p>Loading...</p>
  if (error) return <ErrorMessage resource="position history" />
  if (!data || data.length === 0) {
    return <p>No position history to chart yet this season in this competition.</p>
  }

  const maxPosition = Math.max(...data.map((d) => d.position))

  return (
    <div>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="matchday"
            type="number"
            allowDecimals={false}
            label={{ value: 'Matchday', position: 'insideBottom', offset: -5 }}
          />
          <YAxis
            dataKey="position"
            reversed
            domain={[1, maxPosition]}
            allowDecimals={false}
            label={{ value: 'Position', angle: -90, position: 'insideLeft' }}
          />
          <Tooltip />
          <Line
            type="monotone"
            dataKey="position"
            stroke="var(--color-blue)"
            strokeWidth={2}
            dot
          />
        </LineChart>
      </ResponsiveContainer>
      <p className="text-text-muted text-sm mt-2">
        Reconstructed from match results, not the official table -- may drift from it (points
        deductions, tiebreakers not captured here), and omits a team that hasn't yet played the
        season's latest matchday.
      </p>
    </div>
  )
}
