import { useState } from 'react'
import { useAllTeams } from '../../hooks/useTeams'
import { useHeadToHead, useHeadToHeadMatches } from '../../hooks/useHeadToHead'
import { formatKickoff } from '../../lib/formatKickoff'
import { formatScore } from '../../lib/formatScore'
import { ErrorMessage } from '../ErrorMessage'

interface CompareTabProps {
  teamId: number | null
  teamName?: string
  active: boolean
}

export function CompareTab({ teamId, teamName, active }: CompareTabProps) {
  const [opponentId, setOpponentId] = useState<number | undefined>(undefined)
  const { data: allTeams, isLoading: teamsLoading, error: teamsError } = useAllTeams(active)
  const opponents = (allTeams ?? []).filter((t) => t.team_id !== teamId)

  const {
    data: record,
    isLoading: recordLoading,
    error: recordError,
  } = useHeadToHead(teamId, opponentId, active)
  const {
    data: matches,
    isLoading: matchesLoading,
    error: matchesError,
  } = useHeadToHeadMatches(teamId, opponentId, active && record !== null && record !== undefined)

  if (!active) return null
  if (teamsLoading) return <p>Loading...</p>
  if (teamsError) return <ErrorMessage resource="clubs" />

  const opponentName = opponents.find((t) => t.team_id === opponentId)?.team_name

  return (
    <div>
      <select
        value={opponentId ?? ''}
        onChange={(e) => setOpponentId(e.target.value ? Number(e.target.value) : undefined)}
        className="rounded border border-line px-2 py-1"
      >
        <option value="">Compare against...</option>
        {opponents.map((t) => (
          <option key={t.team_id} value={t.team_id}>
            {t.team_name}
          </option>
        ))}
      </select>

      {opponentId !== undefined && (
        <>
          {recordLoading && <p>Loading...</p>}
          {recordError && <ErrorMessage resource="head-to-head record" />}
          {!recordLoading && !recordError && record === null && (
            <p className="mt-3">These two clubs haven't played each other yet.</p>
          )}
          {!recordLoading && !recordError && record && (
            <>
              <p className="mt-3">
                Played {record.matches_played}: {teamName ?? 'This team'} {record.team_1_wins}W,{' '}
                {opponentName} {record.team_2_wins}W, {record.draws}D ({record.team_1_goals}-
                {record.team_2_goals} goals)
              </p>
              <h3 className="font-semibold mt-4">Past meetings</h3>
              {matchesLoading && <p>Loading...</p>}
              {matchesError && <ErrorMessage resource="past meetings" />}
              {matches && (
                <table className="w-full text-lg mt-2">
                  <thead>
                    <tr className="text-left text-text-muted text-base uppercase">
                      <th>Kickoff</th>
                      <th>Competition</th>
                      <th>Home</th>
                      <th className="text-center">Score</th>
                      <th>Away</th>
                    </tr>
                  </thead>
                  <tbody>
                    {matches.map((m) => (
                      <tr
                        key={`${m.kickoff_utc}-${m.home_team_name}`}
                        className="border-t border-line"
                      >
                        <td>{formatKickoff(m.kickoff_utc, m.kickoff_time_confirmed)}</td>
                        <td>{m.competition_name}</td>
                        <td>{m.home_team_name}</td>
                        <td className="text-center">
                          {formatScore(m.full_time_home, m.full_time_away)}
                        </td>
                        <td>{m.away_team_name}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </>
          )}
        </>
      )}
    </div>
  )
}
