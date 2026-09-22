import { useEffect, useState } from 'react'
import * as Tabs from '@radix-ui/react-tabs'
import { useCurrentSeason, useLeagueSeasons } from '../hooks/useLeagueSeasons'
import { DetailDialog } from './DetailDialog'
import { StandingsTab } from './tabs/StandingsTab'
import { RecentResultsTab } from './tabs/RecentResultsTab'
import { FixturesTab } from './tabs/FixturesTab'
import { LeadersTab } from './tabs/LeadersTab'
import { LeaguePositionBumpChart } from './tabs/LeaguePositionBumpChart'

interface LeagueDetailDialogProps {
  competitionCode: string | null
  competitionName?: string
  competitionEmblem?: string | null
  onClose: () => void
}

const TABS = [
  { value: 'table', label: 'Table' },
  { value: 'movement', label: 'Movement' },
  { value: 'results', label: 'Recent Results' },
  { value: 'fixtures', label: 'Fixtures' },
  { value: 'leaders', label: 'Leaders' },
]

export function LeagueDetailDialog({
  competitionCode,
  competitionName,
  competitionEmblem,
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
    <DetailDialog
      open={isOpen}
      onOpenChange={(open) => !open && onClose()}
      title={competitionName ?? competitionCode ?? ''}
      titleIcon={competitionEmblem}
      tabs={TABS}
      activeTab={activeTab}
      onTabChange={setActiveTab}
      headerExtra={
        seasons && seasons.length > 0 ? (
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
        ) : undefined
      }
    >
      <Tabs.Content value="table" className="pt-6">
        <StandingsTab
          competitionCode={code}
          seasonId={seasonId}
          isCurrentSeason={seasonId === currentSeasonId}
          active={activeTab === 'table'}
        />
      </Tabs.Content>
      <Tabs.Content value="movement" className="pt-6">
        <LeaguePositionBumpChart
          competitionCode={code}
          seasonId={seasonId}
          active={activeTab === 'movement'}
        />
      </Tabs.Content>
      <Tabs.Content value="results" className="pt-6">
        <RecentResultsTab
          competitionCode={code}
          seasonId={seasonId}
          active={activeTab === 'results'}
        />
      </Tabs.Content>
      <Tabs.Content value="fixtures" className="pt-6">
        <FixturesTab
          competitionCode={code}
          seasonId={seasonId}
          active={activeTab === 'fixtures'}
        />
      </Tabs.Content>
      <Tabs.Content value="leaders" className="pt-6">
        <LeadersTab
          competitionCode={code}
          seasonId={seasonId}
          active={activeTab === 'leaders'}
        />
      </Tabs.Content>
    </DetailDialog>
  )
}
