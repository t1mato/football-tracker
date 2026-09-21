import { useState } from 'react'
import * as Tabs from '@radix-ui/react-tabs'
import { PlayerDirectoryTable } from '../components/PlayerDirectoryTable'
import { PlayerDetailDialog } from '../components/PlayerDetailDialog'
import { GoldenBootTab } from '../components/GoldenBootTab'

export function Players() {
  const [activeTab, setActiveTab] = useState('directory')
  const [selectedPlayerId, setSelectedPlayerId] = useState<number | null>(null)

  return (
    <div className="p-6">
      <h1 className="font-display text-4xl uppercase mb-6">Players</h1>
      <Tabs.Root value={activeTab} onValueChange={setActiveTab}>
        <Tabs.List className="flex gap-4 border-b border-line mb-4">
          <Tabs.Trigger value="directory" className="pb-2">
            Directory
          </Tabs.Trigger>
          <Tabs.Trigger value="leaderboard" className="pb-2">
            Golden Boot
          </Tabs.Trigger>
        </Tabs.List>
        <Tabs.Content value="directory">
          <PlayerDirectoryTable onSelectPlayer={(id) => setSelectedPlayerId(id)} />
        </Tabs.Content>
        <Tabs.Content value="leaderboard">
          <GoldenBootTab active={activeTab === 'leaderboard'} />
        </Tabs.Content>
      </Tabs.Root>
      <PlayerDetailDialog
        playerId={selectedPlayerId}
        onClose={() => setSelectedPlayerId(null)}
      />
    </div>
  )
}
