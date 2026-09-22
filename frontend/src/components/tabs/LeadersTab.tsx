import { useLeagueScorers } from '../../hooks/useLeagueScorers'
import { ErrorMessage } from '../ErrorMessage'

interface LeadersTabProps {
  competitionCode: string
  seasonId: number | undefined
  active: boolean
}

export function LeadersTab({ competitionCode, seasonId, active }: LeadersTabProps) {
  const { data, isLoading, error } = useLeagueScorers(competitionCode, seasonId, active)

  if (!active) return null
  if (isLoading) return <p>Loading...</p>
  if (error) return <ErrorMessage resource="leaders" />
  if (!data || data.length === 0) return <p>No scorer data yet for this competition/season.</p>

  return (
    <table className="w-full text-lg">
      <thead>
        <tr className="text-left text-text-muted text-base uppercase">
          <th className="pb-3">Rank</th>
          <th className="pb-3">Player</th>
          <th className="pb-3">Club</th>
          <th className="pb-3 text-center">G</th>
          <th className="pb-3 text-center">A</th>
          <th className="pb-3 text-center">MP</th>
          <th className="pb-3 text-center">Pen</th>
        </tr>
      </thead>
      <tbody>
        {data.map((row) => (
          <tr key={`${row.rank}-${row.player_name}`} className="border-t border-line">
            <td>{row.rank}</td>
            <td className="flex items-center gap-2.5 py-3">
              {row.crest && <img src={row.crest} alt="" className="w-6 h-6 object-contain" />}
              {row.player_name}
            </td>
            <td>{row.team_name}</td>
            <td className="text-center">{row.goals}</td>
            <td className="text-center">{row.assists}</td>
            <td className="text-center">{row.played_matches}</td>
            <td className="text-center">{row.penalties}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
