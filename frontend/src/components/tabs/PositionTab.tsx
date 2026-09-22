import { Line, LineChart, ResponsiveContainer, XAxis, YAxis } from 'recharts'
import type { DotItemDotProps } from 'recharts'
import { useTeamPositionHistory } from '../../hooks/useTeamStats'
import { useClubColors } from '../../hooks/useClubColors'
import { ErrorMessage } from '../ErrorMessage'

interface PositionTabProps {
  teamId: number | null
  teamName?: string
  teamCrest?: string | null
  leagueCode: string
  leagueSeasonId: number | undefined
  active: boolean
}

const FALLBACK_COLOR = 'var(--color-blue)'
const PX_PER_MATCHDAY = 42
const MIN_WIDTH = 500
const RIGHT_MARGIN = 200

/** Same "numbered circle at every matchday, crest+name at the last one"
 * node as LeaguePositionBumpChart's nodeDot -- deliberately reused look,
 * just for a single line, so there's no tie-offset logic to carry over
 * (a team can never tie with itself). */
function nodeDot(teamName: string, teamCrest: string | null, color: string, lastMatchday: number) {
  return function NodeDot(props: DotItemDotProps) {
    const { cx, cy, payload, value } = props
    if (cx == null || cy == null) return <g />
    const isEnd = payload?.matchday === lastMatchday
    return (
      <g>
        <circle cx={cx} cy={cy} r={10} fill={color} />
        <text
          x={cx}
          y={cy}
          textAnchor="middle"
          dominantBaseline="central"
          fill="var(--color-surface)"
          fontSize={10}
          fontWeight={800}
        >
          {String(value)}
        </text>
        {isEnd && (
          <>
            {teamCrest && <image href={teamCrest} x={cx + 18} y={cy - 9} width={18} height={18} />}
            <text
              x={cx + (teamCrest ? 42 : 16)}
              y={cy}
              textAnchor="start"
              dominantBaseline="central"
              fill={color}
              fontSize={13}
              fontWeight={700}
            >
              {teamName}
            </text>
          </>
        )}
      </g>
    )
  }
}

export function PositionTab({
  teamId,
  teamName,
  teamCrest,
  leagueCode,
  leagueSeasonId,
  active,
}: PositionTabProps) {
  const { data, isLoading, error } = useTeamPositionHistory(
    teamId,
    leagueCode,
    leagueSeasonId,
    active
  )
  const { data: clubColors } = useClubColors()

  if (!active) return null
  if (isLoading) return <p>Loading...</p>
  if (error) return <ErrorMessage resource="position history" />
  if (!data || data.length === 0) {
    return <p>No position history to chart yet this season in this competition.</p>
  }

  const maxPosition = Math.max(...data.map((d) => d.position))
  const firstMatchday = data[0].matchday
  const lastMatchday = data[data.length - 1].matchday
  const color = (teamId !== null ? clubColors?.[String(teamId)] : undefined) ?? FALLBACK_COLOR
  const matchdayTicks = data.map((d) => d.matchday)
  const chartWidth =
    Math.max(MIN_WIDTH, (lastMatchday - firstMatchday + 1) * PX_PER_MATCHDAY) + RIGHT_MARGIN
  const chartHeight = Math.max(280, maxPosition * 30)

  return (
    <div>
      <div className="overflow-x-auto">
        <ResponsiveContainer width={chartWidth} height={chartHeight + 40}>
          <LineChart data={data} margin={{ top: 20, right: RIGHT_MARGIN, bottom: 40, left: 8 }}>
            <XAxis
              dataKey="matchday"
              type="number"
              domain={[firstMatchday, lastMatchday]}
              ticks={matchdayTicks}
              interval={0}
              allowDecimals={false}
              tickLine={false}
              axisLine={false}
              tickMargin={16}
              tick={{ fill: 'var(--color-text-muted)', fontSize: 12 }}
              label={{
                value: 'Matchday',
                position: 'insideBottom',
                offset: -12,
                fill: 'var(--color-text-muted)',
                fontSize: 12,
              }}
            />
            <YAxis
              reversed
              domain={[1, maxPosition]}
              allowDecimals={false}
              padding={{ top: 20, bottom: 20 }}
              hide
            />
            <Line
              dataKey="position"
              stroke={color}
              strokeWidth={2}
              dot={nodeDot(teamName ?? 'This club', teamCrest ?? null, color, lastMatchday)}
              activeDot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="text-text-muted text-lg mt-3">
        Reconstructed from match results, not the official table -- may drift from it (points
        deductions, tiebreakers not captured here), and omits a matchday this team hasn't played
        yet.
      </p>
    </div>
  )
}
