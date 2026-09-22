import type { Competition } from '../hooks/useCompetitions'

interface LeagueCardProps {
  competition: Competition
  selected?: boolean
  onView: () => void
}

export function LeagueCard({ competition, selected = false, onView }: LeagueCardProps) {
  return (
    <button
      type="button"
      onClick={onView}
      className={`text-left rounded-xl border p-5 flex items-center gap-3.5 bg-surface ${
        selected ? 'border-blue ring-3 ring-blue/20' : 'border-line'
      }`}
    >
      {competition.emblem && (
        <img src={competition.emblem} alt="" className="w-8 h-8 object-contain flex-none" />
      )}
      <div className="flex-1 min-w-0">
        <p className="font-bold text-lg truncate">{competition.competition_name}</p>
        <div className="flex items-center gap-2 text-base text-text-muted mt-0.5">
          {competition.area_flag && (
            <span className="w-4 h-4 rounded-full overflow-hidden flex-none bg-surface-2">
              <img src={competition.area_flag} alt="" className="w-full h-full object-cover" />
            </span>
          )}
          <span>{competition.area_name}</span>
        </div>
      </div>
    </button>
  )
}
