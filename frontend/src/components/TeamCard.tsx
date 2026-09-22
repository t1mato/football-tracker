import type { TeamRow } from '../hooks/useTeams'

interface TeamCardProps {
  team: TeamRow
  selected?: boolean
  onView: () => void
}

export function TeamCard({ team, selected = false, onView }: TeamCardProps) {
  return (
    <button
      type="button"
      onClick={onView}
      className={`text-left rounded-xl border p-5 flex items-center gap-3.5 bg-surface ${
        selected ? 'border-blue ring-3 ring-blue/20' : 'border-line'
      }`}
    >
      {team.crest && (
        <img
          src={team.crest}
          alt={team.team_name}
          className="w-8 h-8 object-contain flex-none"
        />
      )}
      <div className="flex-1 min-w-0">
        <p className="font-bold text-lg truncate">{team.team_name}</p>
      </div>
    </button>
  )
}
