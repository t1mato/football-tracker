import { useEffect, useState } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import * as Tabs from '@radix-ui/react-tabs'
import { useCurrentSeason, useLeagueSeasons } from '../hooks/useLeagueSeasons'
import { StandingsTab } from './tabs/StandingsTab'
import { RecentResultsTab } from './tabs/RecentResultsTab'
import { FixturesTab } from './tabs/FixturesTab'
import { LeadersTab } from './tabs/LeadersTab'
import { StreaksTab } from './tabs/StreaksTab'

interface LeagueDetailDialogProps {
  competitionCode: string | null
  competitionName?: string
  onClose: () => void
}

export function LeagueDetailDialog({
  competitionCode,
  competitionName,
  onClose,
}: LeagueDetailDialogProps) {
  const [activeTab, setActiveTab] = useState('table')
  const isOpen = competitionCode !== null
  const code = competitionCode ?? ''
  const { data: seasons } = useLeagueSeasons(code, isOpen)
  const { data: currentSeasonId } = useCurrentSeason(code, isOpen)
  const [selectedSeason, setSelectedSeason] = useState<number | undefined>(undefined)
  const seasonId = selectedSeason ?? currentSeasonId

  // Season ids are disjoint per competition, and this dialog stays mounted
  // across opens/closes -- without this, reopening on a different
  // competition would carry over a stale season selection and tab.
  useEffect(() => {
    setSelectedSeason(undefined)
    setActiveTab('table')
  }, [competitionCode])

  return (
    <Dialog.Root open={competitionCode !== null} onOpenChange={(open) => !open && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/40" />
        <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-surface rounded-xl p-6 max-w-3xl w-full max-h-[85vh] overflow-y-auto">
          <Dialog.Title className="font-display text-3xl uppercase">
            {competitionName ?? competitionCode}
          </Dialog.Title>
          {seasons && seasons.length > 0 && (
            <select
              value={seasonId ?? ''}
              onChange={(e) => setSelectedSeason(Number(e.target.value))}
              className="mt-2 rounded border border-line px-2 py-1"
            >
              {seasons.map((s) => (
                <option key={s.season_id} value={s.season_id}>
                  {s.start_date.slice(0, 4)}/{s.end_date.slice(2, 4)}
                </option>
              ))}
            </select>
          )}
          <Tabs.Root value={activeTab} onValueChange={setActiveTab} className="mt-4">
            <Tabs.List className="flex gap-4 border-b border-line">
              <Tabs.Trigger value="table" className="pb-2">Table</Tabs.Trigger>
              <Tabs.Trigger value="results" className="pb-2">Recent Results</Tabs.Trigger>
              <Tabs.Trigger value="fixtures" className="pb-2">Fixtures</Tabs.Trigger>
              <Tabs.Trigger value="leaders" className="pb-2">Leaders</Tabs.Trigger>
              <Tabs.Trigger value="streaks" className="pb-2">Streaks</Tabs.Trigger>
            </Tabs.List>
            <Tabs.Content value="table" className="pt-4">
              <StandingsTab
                competitionCode={code}
                seasonId={seasonId}
                isCurrentSeason={seasonId === currentSeasonId}
                active={activeTab === 'table'}
              />
            </Tabs.Content>
            <Tabs.Content value="results" className="pt-4">
              <RecentResultsTab
                competitionCode={code}
                seasonId={seasonId}
                active={activeTab === 'results'}
              />
            </Tabs.Content>
            <Tabs.Content value="fixtures" className="pt-4">
              <FixturesTab
                competitionCode={code}
                seasonId={seasonId}
                active={activeTab === 'fixtures'}
              />
            </Tabs.Content>
            <Tabs.Content value="leaders" className="pt-4">
              <LeadersTab
                competitionCode={code}
                seasonId={seasonId}
                active={activeTab === 'leaders'}
              />
            </Tabs.Content>
            <Tabs.Content value="streaks" className="pt-4">
              <StreaksTab
                competitionCode={code}
                currentSeasonId={currentSeasonId}
                active={activeTab === 'streaks'}
              />
            </Tabs.Content>
          </Tabs.Root>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
