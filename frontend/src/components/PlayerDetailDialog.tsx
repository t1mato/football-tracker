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
        <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-surface rounded-xl p-6 max-w-3xl w-full max-h-[85vh] overflow-y-auto">
          {bioLoading && <p>Loading...</p>}
          {bioError && <p>{bioError.message}</p>}
          {bio && (
            <>
              <Dialog.Title className="font-display text-3xl uppercase">
                {bio.player_name}
              </Dialog.Title>
              {bio.crest && (
                <img src={bio.crest} alt="" className="w-12 h-12 object-contain mt-2" />
              )}
              <div className="grid grid-cols-3 gap-3 mt-3">
                <div className="rounded-lg border border-line p-3 text-center">
                  <p className="text-xs uppercase text-text-muted">Position</p>
                  <p className="text-xl font-semibold">{bio.position ?? 'Unknown'}</p>
                </div>
                <div className="rounded-lg border border-line p-3 text-center">
                  <p className="text-xs uppercase text-text-muted">Nationality</p>
                  <p className="text-xl font-semibold">{bio.nationality ?? 'Unknown'}</p>
                </div>
                <div className="rounded-lg border border-line p-3 text-center">
                  <p className="text-xs uppercase text-text-muted">Age</p>
                  <p className="text-xl font-semibold">
                    {bio.date_of_birth ? playerAge(bio.date_of_birth) : 'Unknown'}
                  </p>
                </div>
              </div>
              <p className="text-sm text-text-muted mt-2">Club: {bio.team_name ?? 'Unknown'}</p>

              <h3 className="font-semibold mt-4">Scoring history</h3>
              {historyLoading && <p>Loading...</p>}
              {historyError && <p>Couldn't load scoring history.</p>}
              {history && history.length === 0 && (
                <p>No goal/assist contributions recorded for this player.</p>
              )}
              {history && history.length > 0 && (
                <table className="w-full text-sm mt-2">
                  <thead>
                    <tr className="text-left text-text-muted text-xs uppercase">
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
