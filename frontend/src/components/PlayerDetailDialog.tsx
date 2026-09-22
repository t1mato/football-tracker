import * as Dialog from '@radix-ui/react-dialog'
import { usePlayerBio, usePlayerScoringHistory } from '../hooks/usePlayers'
import { playerAge } from '../lib/playerAge'
import { seasonLabel } from '../lib/seasonLabel'

interface PlayerDetailDialogProps {
  playerId: number | null
  onClose: () => void
}

export function PlayerDetailDialog({ playerId, onClose }: PlayerDetailDialogProps) {
  const isOpen = playerId !== null
  const { data: bio, isLoading: bioLoading, error: bioError } = usePlayerBio(playerId, isOpen)
  const {
    data: history,
    isLoading: historyLoading,
    error: historyError,
  } = usePlayerScoringHistory(playerId, isOpen)

  return (
    <Dialog.Root open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/40" />
        <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-surface rounded-2xl shadow-card p-8 max-w-5xl w-full max-h-[90vh] overflow-y-auto">
          <div className="flex items-center gap-4">
            {bio?.crest && <img src={bio.crest} alt="" className="w-12 h-12 object-contain" />}
            <Dialog.Title className="font-display text-4xl uppercase">
              {bio?.player_name ?? 'Player'}
            </Dialog.Title>
          </div>
          {bioLoading && <p>Loading...</p>}
          {bioError && <p>{bioError.message}</p>}
          {bio && (
            <>
              <div className="grid grid-cols-3 gap-4 mt-5">
                <div className="rounded-lg bg-surface-2 p-4 flex flex-col gap-1">
                  <p className="font-display text-3xl leading-none">{bio.position ?? 'Unknown'}</p>
                  <p className="text-sm uppercase tracking-wide text-text-muted">
                    Position
                  </p>
                </div>
                <div className="rounded-lg bg-surface-2 p-4 flex flex-col gap-1">
                  <p className="font-display text-3xl leading-none">
                    {bio.nationality ?? 'Unknown'}
                  </p>
                  <p className="text-sm uppercase tracking-wide text-text-muted">
                    Nationality
                  </p>
                </div>
                <div className="rounded-lg bg-surface-2 p-4 flex flex-col gap-1">
                  <p className="font-display text-3xl leading-none">
                    {bio.date_of_birth ? playerAge(bio.date_of_birth) : 'Unknown'}
                  </p>
                  <p className="text-sm uppercase tracking-wide text-text-muted">Age</p>
                </div>
              </div>
              <p className="text-lg text-text-muted mt-4">Club: {bio.team_name ?? 'Unknown'}</p>

              <h3 className="font-semibold text-lg mt-6 mb-2">Scoring history</h3>
              {historyLoading && <p>Loading...</p>}
              {historyError && <p>Couldn't load scoring history.</p>}
              {history && history.length === 0 && (
                <p>No goal/assist contributions recorded for this player.</p>
              )}
              {history && history.length > 0 && (
                <table className="w-full text-lg mt-2">
                  <thead>
                    <tr className="text-left text-text-muted text-base uppercase">
                      <th>Season</th>
                      <th>Competition</th>
                      <th className="text-center">G</th>
                      <th className="text-center">A</th>
                      <th className="text-center">MP</th>
                      <th className="text-center">Pen</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((row) => (
                      <tr
                        key={`${row.competition_name}-${row.start_date}`}
                        className="border-t border-line"
                      >
                        <td>{seasonLabel(row.start_date, row.end_date)}</td>
                        <td>{row.competition_name}</td>
                        <td className="text-center">{row.goals}</td>
                        <td className="text-center">{row.assists}</td>
                        <td className="text-center">{row.played_matches}</td>
                        <td className="text-center">{row.penalties}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
