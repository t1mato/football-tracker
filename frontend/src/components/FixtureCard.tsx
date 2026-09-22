import type { ReactNode } from 'react'
import { formatKickoffParts } from '../lib/formatKickoffParts'

const STATUS_LABELS: Record<string, string> = {
  SCHEDULED: 'Scheduled',
  TIMED: 'Confirmed',
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
  competitionName,
  competitionEmblem,
  onClick,
  children,
}: FixtureCardProps) {
  const { time, date } = formatKickoffParts(kickoffUtc, kickoffTimeConfirmed)
  const statusLabel = status ? (STATUS_LABELS[status] ?? status) : null

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
          {time && (
            <span className="flex items-center gap-1.5 text-text-muted">
              <ClockIcon />
              {time}
            </span>
          )}
          <span className="text-text-muted text-sm">{date}</span>
          {statusLabel && (
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
