import { useState } from 'react'
import * as Tabs from '@radix-ui/react-tabs'
import { useLeagueScorers } from '../../hooks/useLeagueScorers'
import { useLeagueAssists } from '../../hooks/useLeagueAssists'
import { ErrorMessage } from '../ErrorMessage'

interface LeadersTabProps {
  competitionCode: string
  seasonId: number | undefined
  active: boolean
}

const SUB_TAB_TRIGGER_CLASS =
  'pb-3 font-bold text-lg text-text-muted border-b-2 border-transparent data-[state=active]:text-blue data-[state=active]:border-blue'

function ScorersTable({ competitionCode, seasonId, active }: LeadersTabProps) {
  const { data, isLoading, error } = useLeagueScorers(competitionCode, seasonId, active)

  if (!active) return null
  if (isLoading) return <p>Loading...</p>
  if (error) return <ErrorMessage resource="top scorers" />
  if (!data || data.length === 0) return <p>No scorer data yet for this competition/season.</p>

  return (
    <table className="w-full text-lg">
      <thead>
        <tr className="text-left text-text-muted text-base uppercase">
          <th className="pb-3 px-2">Rank</th>
          <th className="pb-3 px-2">Player</th>
          <th className="pb-3 px-2">Club</th>
          <th className="pb-3 px-2 text-center">P</th>
          <th className="pb-3 px-2 text-center">G</th>
          <th className="pb-3 px-2 text-center">Pen</th>
        </tr>
      </thead>
      <tbody>
        {data.map((row) => (
          <tr key={`${row.rank}-${row.player_name}`} className="border-t border-line">
            <td className="py-3 px-2">{row.rank}</td>
            <td className="flex items-center gap-2.5 py-3 px-2">
              {row.crest && <img src={row.crest} alt="" className="w-6 h-6 object-contain" />}
              {row.player_name}
            </td>
            <td className="px-2">{row.team_name}</td>
            <td className="px-2 text-center">{row.played_matches}</td>
            <td className="px-2 text-center">{row.goals}</td>
            <td className="px-2 text-center">{row.penalties}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function AssistsTable({ competitionCode, seasonId, active }: LeadersTabProps) {
  const { data, isLoading, error } = useLeagueAssists(competitionCode, seasonId, active)

  if (!active) return null
  if (isLoading) return <p>Loading...</p>
  if (error) return <ErrorMessage resource="top assists" />
  if (!data || data.length === 0) return <p>No assist data yet for this competition/season.</p>

  return (
    <table className="w-full text-lg">
      <thead>
        <tr className="text-left text-text-muted text-base uppercase">
          <th className="pb-3 px-2">Rank</th>
          <th className="pb-3 px-2">Player</th>
          <th className="pb-3 px-2">Club</th>
          <th className="pb-3 px-2 text-center">P</th>
          <th className="pb-3 px-2 text-center">A</th>
        </tr>
      </thead>
      <tbody>
        {data.map((row) => (
          <tr key={`${row.rank}-${row.player_name}`} className="border-t border-line">
            <td className="py-3 px-2">{row.rank}</td>
            <td className="flex items-center gap-2.5 py-3 px-2">
              {row.crest && <img src={row.crest} alt="" className="w-6 h-6 object-contain" />}
              {row.player_name}
            </td>
            <td className="px-2">{row.team_name}</td>
            <td className="px-2 text-center">{row.played_matches}</td>
            <td className="px-2 text-center">{row.assists}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export function LeadersTab({ competitionCode, seasonId, active }: LeadersTabProps) {
  const [subTab, setSubTab] = useState('scorers')

  // Unmounted (not just hidden) while the outer Leaders tab isn't active,
  // same discipline every other tab component in this dialog follows --
  // otherwise both sub-tabs' queries would fire as soon as the dialog
  // mounts, not just once Leaders is actually clicked.
  if (!active) return null

  return (
    <Tabs.Root value={subTab} onValueChange={setSubTab}>
      <Tabs.List className="flex gap-6 border-b border-line mb-6">
        <Tabs.Trigger value="scorers" className={SUB_TAB_TRIGGER_CLASS}>
          Top Scorers
        </Tabs.Trigger>
        <Tabs.Trigger value="assists" className={SUB_TAB_TRIGGER_CLASS}>
          Top Assists
        </Tabs.Trigger>
      </Tabs.List>
      <Tabs.Content value="scorers">
        <ScorersTable
          competitionCode={competitionCode}
          seasonId={seasonId}
          active={subTab === 'scorers'}
        />
      </Tabs.Content>
      <Tabs.Content value="assists">
        <AssistsTable
          competitionCode={competitionCode}
          seasonId={seasonId}
          active={subTab === 'assists'}
        />
      </Tabs.Content>
    </Tabs.Root>
  )
}
