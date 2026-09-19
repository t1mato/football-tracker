import type { Competition } from '../hooks/useCompetitions'

interface LeagueCardProps {
  competition: Competition
  onView: () => void
}

export function LeagueCard({ competition, onView }: LeagueCardProps) {
  return (
    <div className="rounded-xl border border-line bg-surface p-4 flex items-center gap-3">
      {competition.emblem && (
        <img src={competition.emblem} alt="" className="w-12 h-12 object-contain flex-none" />
      )}
      <div className="flex-1 min-w-0">
        <p className="font-semibold">{competition.competition_name}</p>
        <div className="flex items-center gap-1.5 text-sm text-text-muted">
          {competition.area_flag && (
            <img src={competition.area_flag} alt="" className="w-5 h-5 rounded-full object-cover" />
          )}
          <span>{competition.area_name}</span>
        </div>
      </div>
      <button
        type="button"
        onClick={onView}
        className="rounded-lg border border-line px-3 py-1.5 text-sm font-medium"
      >
        View
      </button>
    </div>
  )
}
