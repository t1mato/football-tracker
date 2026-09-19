import { useLeagueScorers } from '../../hooks/useLeagueScorers'

interface LeadersTabProps {
  competitionCode: string
  seasonId: number | undefined
  active: boolean
}

export function LeadersTab({ competitionCode, seasonId, active }: LeadersTabProps) {
  const { data, isLoading } = useLeagueScorers(competitionCode, seasonId, active)

  if (!active) return null
  if (isLoading) return <p>Loading...</p>
  if (!data || data.length === 0) return <p>No scorer data yet for this competition/season.</p>

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-text-muted text-xs uppercase">
          <th>Rank</th>
          <th>Player</th>
          <th>Team</th>
          <th className="text-center">G</th>
          <th className="text-center">A</th>
          <th className="text-center">MP</th>
        </tr>
      </thead>
      <tbody>
        {data.map((row) => (
          <tr key={`${row.rank}-${row.player_name}`} className="border-t border-line">
            <td>{row.rank}</td>
            <td className="flex items-center gap-2 py-1.5">
              {row.crest && <img src={row.crest} alt="" className="w-5 h-5 object-contain" />}
              {row.player_name}
            </td>
            <td>{row.team_name}</td>
            <td className="text-center">{row.goals}</td>
            <td className="text-center">{row.assists}</td>
            <td className="text-center">{row.played_matches}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
