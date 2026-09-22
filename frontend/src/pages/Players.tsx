import { useState } from 'react'
import { PlayerDirectoryTable } from '../components/PlayerDirectoryTable'
import { PlayerDetailDialog } from '../components/PlayerDetailDialog'
import { Frame } from '../components/Frame'

export function Players() {
  const [selectedPlayerId, setSelectedPlayerId] = useState<number | null>(null)

  return (
    <div>
      <h1 className="font-display text-5xl uppercase mb-8">Players</h1>
      <Frame>
        <PlayerDirectoryTable onSelectPlayer={(id) => setSelectedPlayerId(id)} />
      </Frame>
      <PlayerDetailDialog
        playerId={selectedPlayerId}
        onClose={() => setSelectedPlayerId(null)}
      />
    </div>
  )
}
