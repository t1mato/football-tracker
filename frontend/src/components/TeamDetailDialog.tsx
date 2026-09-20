import { useEffect, useState } from 'react'
import * as Tabs from '@radix-ui/react-tabs'
import { DetailDialog } from './DetailDialog'
import { FormTab } from './tabs/FormTab'
import { TeamFixturesTab } from './tabs/TeamFixturesTab'
import { StatsTab } from './tabs/StatsTab'
import { PositionTab } from './tabs/PositionTab'

interface TeamDetailDialogProps {
  teamId: number | null
  teamName?: string
  leagueCode: string
  leagueSeasonId: number | undefined
  onClose: () => void
}

const TABS = [
  { value: 'form', label: 'Form' },
  { value: 'fixtures', label: 'Fixtures' },
  { value: 'stats', label: 'Stats' },
  { value: 'position', label: 'Position' },
  { value: 'streaks', label: 'Streaks' },
  { value: 'compare', label: 'Compare vs...' },
]

export function TeamDetailDialog({
  teamId,
  teamName,
  leagueCode,
  leagueSeasonId,
  onClose,
}: TeamDetailDialogProps) {
  const [activeTab, setActiveTab] = useState('form')
  const isOpen = teamId !== null

  // Same reset discipline as LeagueDetailDialog: this dialog stays
  // permanently mounted, so reopening on a different team without a
  // reset would keep whichever tab was last active instead of
  // defaulting back to Form.
  useEffect(() => {
    setActiveTab('form')
  }, [teamId])

  return (
    <DetailDialog
      open={isOpen}
      onOpenChange={(open) => !open && onClose()}
      title={teamName ?? ''}
      tabs={TABS}
      activeTab={activeTab}
      onTabChange={setActiveTab}
    >
      <Tabs.Content value="form" className="pt-4">
        <FormTab teamId={teamId} active={activeTab === 'form'} />
      </Tabs.Content>
      <Tabs.Content value="fixtures" className="pt-4">
        <TeamFixturesTab teamId={teamId} active={activeTab === 'fixtures'} />
      </Tabs.Content>
      <Tabs.Content value="stats" className="pt-4">
        <StatsTab
          teamId={teamId}
          leagueCode={leagueCode}
          leagueSeasonId={leagueSeasonId}
          active={activeTab === 'stats'}
        />
      </Tabs.Content>
      <Tabs.Content value="position" className="pt-4">
        <PositionTab
          teamId={teamId}
          leagueCode={leagueCode}
          leagueSeasonId={leagueSeasonId}
          active={activeTab === 'position'}
        />
      </Tabs.Content>
      {/* Streaks and Compare Tabs.Content blocks are added in Task 7 and
          Task 8, directly after this comment -- do not remove it, their
          instructions look for it by this exact text. */}
    </DetailDialog>
  )
}
