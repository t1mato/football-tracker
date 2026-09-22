import { useMemo } from 'react'
import { Line, LineChart, ResponsiveContainer, XAxis, YAxis } from 'recharts'
import type { DotItemDotProps } from 'recharts'
import { useLeaguePositionHistory } from '../../hooks/useLeaguePositionHistory'
import { useClubColors } from '../../hooks/useClubColors'
import { ErrorMessage } from '../ErrorMessage'

interface LeaguePositionBumpChartProps {
  competitionCode: string
  seasonId: number | undefined
  active: boolean
}

interface ChartTeam {
  team_id: number
  team_name: string
  crest: string | null
  color: string
}

const teamKey = (id: number) => `team_${id}`
const FALLBACK_COLOR = 'var(--color-text-muted)'
const PX_PER_MATCHDAY = 42
const MIN_WIDTH = 900
const RIGHT_MARGIN = 260
/** How far apart (in px) to nudge two clubs' dots when a reconstructed
 * matchday genuinely ties them on the same position -- common tiebreaks
 * (head-to-head, disciplinary points) aren't reconstructible from match
 * results alone, so rank() legitimately gives both the same number. The
 * line paths themselves are never touched, only where the dot/label for
 * that one matchday renders, so the trajectory stays accurate and only
 * the on-screen circles stop sitting exactly on top of each other. */
const TIE_OFFSET_STEP = 13
const tieKey = (matchday: number, teamId: number) => `${matchday}-${teamId}`

/** A numbered circle at every matchday -- not just the endpoints -- plus
 * the club's crest and name at the very last one, matching the
 * reference's "every checkpoint gets its own labeled node" look. */
function nodeDot(team: ChartTeam, lastMatchday: number, tieOffsets: Map<string, number>) {
  return function NodeDot(props: DotItemDotProps) {
    const { cx, cy: rawCy, payload, value } = props
    const matchday = payload?.matchday
    const isEnd = matchday === lastMatchday
    if (cx == null || rawCy == null) {
      return <g key={`dot-${team.team_id}-${matchday}`} />
    }
    const cy = rawCy + (tieOffsets.get(tieKey(matchday, team.team_id)) ?? 0)
    return (
      <g key={`dot-${team.team_id}-${matchday}`}>
        <circle cx={cx} cy={cy} r={10} fill={team.color} />
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
            {team.crest && (
              <image href={team.crest} x={cx + 18} y={cy - 9} width={18} height={18} />
            )}
            <text
              x={cx + (team.crest ? 42 : 16)}
              y={cy}
              textAnchor="start"
              dominantBaseline="central"
              fill={team.color}
              fontSize={13}
              fontWeight={700}
            >
              {team.team_name}
            </text>
          </>
        )}
      </g>
    )
  }
}

export function LeaguePositionBumpChart({
  competitionCode,
  seasonId,
  active,
}: LeaguePositionBumpChartProps) {
  const { data, isLoading, error } = useLeaguePositionHistory(competitionCode, seasonId, active)
  const { data: clubColors } = useClubColors()

  const { chartData, teams, maxPosition, firstMatchday, lastMatchday, tieOffsets } = useMemo(() => {
    if (!data || data.length === 0) {
      return {
        chartData: [],
        teams: [] as ChartTeam[],
        maxPosition: 0,
        firstMatchday: 0,
        lastMatchday: 0,
        tieOffsets: new Map<string, number>(),
      }
    }
    interface Raw {
      team_id: number
      team_name: string
      crest: string | null
    }
    const teamsById = new Map<number, Raw>()
    const byMatchday = new Map<number, Record<string, number>>()
    let max = 0
    for (const row of data) {
      if (!teamsById.has(row.team_id)) {
        teamsById.set(row.team_id, {
          team_id: row.team_id,
          team_name: row.team_name,
          crest: row.crest,
        })
      }
      if (!byMatchday.has(row.matchday)) byMatchday.set(row.matchday, {})
      byMatchday.get(row.matchday)![teamKey(row.team_id)] = row.position
      if (row.position > max) max = row.position
    }
    // Only plot a matchday once every club in the competition has actually
    // played it -- fixtures for one matchday spread across several days,
    // so a partially-played matchday would show some clubs' positions a
    // match ahead of others, a misleading snapshot rather than a real one.
    const totalTeams = teamsById.size
    const points = Array.from(byMatchday.entries())
      .filter(([, positions]) => Object.keys(positions).length === totalTeams)
      .sort(([a], [b]) => a - b)
      .map(([matchday, positions]) => ({ matchday, ...positions }))
    const chartTeams: ChartTeam[] = Array.from(teamsById.values()).map((t) => ({
      team_id: t.team_id,
      team_name: t.team_name,
      crest: t.crest,
      color: clubColors?.[String(t.team_id)] ?? FALLBACK_COLOR,
    }))

    const tieOffsets = new Map<string, number>()
    const teamIds = Array.from(teamsById.keys())
    for (const point of points) {
      const byPosition = new Map<number, number[]>()
      for (const id of teamIds) {
        const pos = (point as Record<string, number>)[teamKey(id)]
        if (pos === undefined) continue
        if (!byPosition.has(pos)) byPosition.set(pos, [])
        byPosition.get(pos)!.push(id)
      }
      for (const tiedIds of byPosition.values()) {
        if (tiedIds.length < 2) continue
        tiedIds.sort((a, b) => a - b)
        const n = tiedIds.length
        tiedIds.forEach((id, i) => {
          tieOffsets.set(tieKey(point.matchday, id), (i - (n - 1) / 2) * TIE_OFFSET_STEP)
        })
      }
    }

    return {
      chartData: points,
      teams: chartTeams,
      maxPosition: max,
      firstMatchday: points[0]?.matchday ?? 0,
      lastMatchday: points[points.length - 1]?.matchday ?? 0,
      tieOffsets,
    }
  }, [data, clubColors])

  if (!active) return null
  if (isLoading) return <p>Loading...</p>
  if (error) return <ErrorMessage resource="position history" />
  if (chartData.length === 0) {
    return <p>No position history to chart yet this season in this competition.</p>
  }

  const matchdayCount = lastMatchday - firstMatchday + 1
  const chartWidth = Math.max(MIN_WIDTH, matchdayCount * PX_PER_MATCHDAY) + RIGHT_MARGIN
  const chartHeight = Math.max(460, maxPosition * 34)
  const matchdayTicks = chartData.map((p) => p.matchday)

  return (
    <div>
      <div className="overflow-x-auto">
        <ResponsiveContainer width={chartWidth} height={chartHeight + 50}>
          <LineChart
            data={chartData}
            margin={{ top: 24, right: RIGHT_MARGIN, bottom: 56, left: 8 }}
          >
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
                offset: -18,
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
            {teams.map((t) => (
              <Line
                key={t.team_id}
                dataKey={teamKey(t.team_id)}
                stroke={t.color}
                strokeWidth={2}
                dot={nodeDot(t, lastMatchday, tieOffsets)}
                activeDot={false}
                isAnimationActive={false}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="text-text-muted text-lg mt-3">
        Every club&apos;s league position after each completed matchday. Reconstructed from match
        results, not the official table.
      </p>
    </div>
  )
}
