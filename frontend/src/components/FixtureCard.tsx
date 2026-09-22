import type { ReactNode } from 'react'
import { formatKickoffParts } from '../lib/formatKickoffParts'
import { formatScore } from '../lib/formatScore'

const STATUS_LABELS: Record<string, string> = {
  SCHEDULED: 'Scheduled',
  TIMED: 'Confirmed',
}

/** Same win/draw/loss palette as ResultBadge, applied as the score's own
 * background instead of a separate letter chip underneath it -- one
 * color-coded rectangle reads faster than a score plus a second badge. */
const RESULT_COLORS: Record<string, string> = {
  W: 'bg-green',
  D: 'bg-yellow',
  L: 'bg-red',
}

function ClockIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className="w-4 h-4"
    >
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 3" />
    </svg>
  )
}

interface FixtureCardProps {
  homeTeamName: string
  homeCrest: string | null
  awayTeamName: string
  awayCrest: string | null
  kickoffUtc: string
  kickoffTimeConfirmed: boolean
  status?: string
  /** Presence of these two (even both null, e.g. an AWARDED match with no
   * recorded score) switches the middle column from a kickoff time/status
   * pill to a final score -- the "completed match" card variant used by
   * Recent Results and a club's Form tab, as opposed to the upcoming-fixture
   * variant used by Fixtures. */
  fullTimeHome?: number | null
  fullTimeAway?: number | null
  /** Only meaningful (and only rendered) for a completed match viewed from
   * one team's perspective -- omitted at the league level, where a result
   * badge would be ambiguous about which side it grades. */
  result?: string | null
  competitionName?: string
  competitionEmblem?: string | null
  onClick?: () => void
  children?: ReactNode
}

export function FixtureCard({
  homeTeamName,
  homeCrest,
  awayTeamName,
  awayCrest,
  kickoffUtc,
  kickoffTimeConfirmed,
  status,
  fullTimeHome,
  fullTimeAway,
  result,
  competitionName,
  competitionEmblem,
  onClick,
  children,
}: FixtureCardProps) {
  const { time, date } = formatKickoffParts(kickoffUtc, kickoffTimeConfirmed)
  const statusLabel = status ? (STATUS_LABELS[status] ?? status) : null
  const isCompleted = fullTimeHome !== undefined && fullTimeAway !== undefined
  const score = isCompleted ? formatScore(fullTimeHome ?? null, fullTimeAway ?? null) : ''

  return (
    <div
      onClick={onClick}
      className={`rounded-2xl border border-line bg-surface shadow-card overflow-hidden ${onClick ? 'cursor-pointer' : ''}`}
    >
      <div className="flex items-center gap-4 p-5">
        <div className="flex-1 flex items-center gap-3 min-w-0">
          {homeCrest && <img src={homeCrest} alt="" className="w-10 h-10 object-contain flex-none" />}
          <span className="font-bold text-lg truncate">{homeTeamName}</span>
        </div>
        <div className="flex-none flex flex-col items-center gap-1">
          {isCompleted ? (
            score &&
            (result ? (
              <span
                className={`rounded-lg px-3 py-1 font-display text-xl font-bold text-white leading-none ${RESULT_COLORS[result] ?? 'bg-text-muted'}`}
              >
                {score}
              </span>
            ) : (
              <span className="font-display text-2xl leading-none">{score}</span>
            ))
          ) : (
            time && (
              <span className="flex items-center gap-1.5 text-text-muted">
                <ClockIcon />
                {time}
              </span>
            )
          )}
          <span className="text-text-muted text-sm">{date}</span>
          {!isCompleted && statusLabel && (
            <span className="rounded-full border border-line px-3 py-1 text-sm font-bold whitespace-nowrap">
              {statusLabel}
            </span>
          )}
        </div>
        <div className="flex-1 flex items-center justify-end gap-3 min-w-0">
          <span className="font-bold text-lg truncate text-right">{awayTeamName}</span>
          {awayCrest && <img src={awayCrest} alt="" className="w-10 h-10 object-contain flex-none" />}
        </div>
      </div>
      {competitionName && (
        <div className="flex items-center gap-2 bg-surface-2 px-5 py-2.5 text-text-muted text-sm border-t border-line">
          {competitionEmblem && (
            <img src={competitionEmblem} alt="" className="w-4 h-4 object-contain" />
          )}
          {competitionName}
        </div>
      )}
      {children && <div className="px-5 pb-5">{children}</div>}
    </div>
  )
}
