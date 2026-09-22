import { useState } from 'react'
import * as Tabs from '@radix-ui/react-tabs'
import { PlayerDirectoryTable } from '../components/PlayerDirectoryTable'
import { PlayerDetailDialog } from '../components/PlayerDetailDialog'
import { GoldenBootTab } from '../components/GoldenBootTab'
import { Frame } from '../components/Frame'

export function Players() {
  const [activeTab, setActiveTab] = useState('directory')
  const [selectedPlayerId, setSelectedPlayerId] = useState<number | null>(null)

  return (
    <div>
      <h1 className="font-display text-5xl uppercase mb-8">Players</h1>
      <Frame>
        <Tabs.Root value={activeTab} onValueChange={setActiveTab}>
          <Tabs.List className="flex gap-6 border-b border-line mb-6">
            <Tabs.Trigger
              value="directory"
              className="pb-3 font-bold text-lg text-text-muted border-b-2 border-transparent data-[state=active]:text-blue data-[state=active]:border-blue"
            >
              Directory
            </Tabs.Trigger>
            <Tabs.Trigger
              value="leaderboard"
              className="pb-3 font-bold text-lg text-text-muted border-b-2 border-transparent data-[state=active]:text-blue data-[state=active]:border-blue"
            >
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
      </Frame>
      <PlayerDetailDialog
        playerId={selectedPlayerId}
        onClose={() => setSelectedPlayerId(null)}
      />
    </div>
  )
}
