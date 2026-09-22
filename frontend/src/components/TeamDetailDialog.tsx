import { useEffect, useState } from 'react'
import * as Tabs from '@radix-ui/react-tabs'
import { DetailDialog } from './DetailDialog'
import { FormTab } from './tabs/FormTab'
import { TeamFixturesTab } from './tabs/TeamFixturesTab'
import { StatsTab } from './tabs/StatsTab'
import { PositionTab } from './tabs/PositionTab'
import { CompareTab } from './tabs/CompareTab'

interface TeamDetailDialogProps {
  teamId: number | null
  teamName?: string
  teamCrest?: string | null
  leagueCode: string
  leagueSeasonId: number | undefined
  onClose: () => void
}

const TABS = [
  { value: 'form', label: 'Form' },
  { value: 'fixtures', label: 'Fixtures' },
  { value: 'stats', label: 'Stats' },
  { value: 'position', label: 'Position' },
  { value: 'compare', label: 'Compare vs...' },
]

export function TeamDetailDialog({
  teamId,
  teamName,
  teamCrest,
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
      titleIcon={teamCrest}
      tabs={TABS}
      activeTab={activeTab}
      onTabChange={setActiveTab}
    >
      <Tabs.Content value="form" className="pt-6">
        <FormTab teamId={teamId} active={activeTab === 'form'} />
      </Tabs.Content>
      <Tabs.Content value="fixtures" className="pt-6">
        <TeamFixturesTab
          teamId={teamId}
          teamName={teamName}
          teamCrest={teamCrest}
          active={activeTab === 'fixtures'}
        />
      </Tabs.Content>
      <Tabs.Content value="stats" className="pt-6">
        <StatsTab
          teamId={teamId}
          leagueCode={leagueCode}
          leagueSeasonId={leagueSeasonId}
          active={activeTab === 'stats'}
        />
      </Tabs.Content>
      <Tabs.Content value="position" className="pt-6">
        <PositionTab
          teamId={teamId}
          leagueCode={leagueCode}
          leagueSeasonId={leagueSeasonId}
          active={activeTab === 'position'}
        />
      </Tabs.Content>
      <Tabs.Content value="compare" className="pt-6">
        <CompareTab teamId={teamId} teamName={teamName} active={activeTab === 'compare'} />
      </Tabs.Content>
    </DetailDialog>
  )
}
