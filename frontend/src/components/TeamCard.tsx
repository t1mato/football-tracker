import type { TeamRow } from '../hooks/useTeams'

interface TeamCardProps {
  team: TeamRow
  onView: () => void
}

export function TeamCard({ team, onView }: TeamCardProps) {
  return (
    <div className="rounded-xl border border-line bg-surface p-4 flex items-center gap-3">
      {team.crest && (
        <img
          src={team.crest}
          alt={team.team_name}
          className="w-12 h-12 object-contain flex-none"
        />
      )}
      <div className="flex-1 min-w-0">
        <p className="font-semibold">{team.team_name}</p>
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
