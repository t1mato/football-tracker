import { useMemo, useState } from 'react'
import { usePlayersDirectory } from '../hooks/usePlayers'
import { ErrorMessage } from './ErrorMessage'

interface PlayerDirectoryTableProps {
  onSelectPlayer: (playerId: number) => void
}

export function PlayerDirectoryTable({ onSelectPlayer }: PlayerDirectoryTableProps) {
  const { data, isLoading, error } = usePlayersDirectory()
  const [search, setSearch] = useState('')
  const [club, setClub] = useState('All')

  const clubs = useMemo(() => {
    const names = new Set(
      (data ?? [])
        .map((p) => p.team_name)
        .filter((name): name is string => name !== null)
    )
    return ['All', ...Array.from(names).sort()]
  }, [data])

  const filtered = useMemo(() => {
    if (!data) return []
    return data.filter((p) => {
      const matchesSearch =
        search === '' || p.player_name.toLowerCase().includes(search.toLowerCase())
      const matchesClub = club === 'All' || p.team_name === club
      return matchesSearch && matchesClub
    })
  }, [data, search, club])

  if (isLoading) return <p>Loading...</p>
  if (error) return <ErrorMessage resource="players" />

  return (
    <div>
      <div className="flex gap-3 mb-3">
        <input
          type="text"
          placeholder="Search by name"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="rounded border border-line px-2 py-1 flex-1"
        />
        <select
          value={club}
          onChange={(e) => setClub(e.target.value)}
          className="rounded border border-line px-2 py-1"
        >
          {clubs.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>
      <p className="text-text-muted text-sm mb-2">{filtered.length} player(s)</p>
      {filtered.length === 0 ? (
        <p>No players match this search/filter.</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-text-muted text-xs uppercase">
              <th></th>
              <th>Player</th>
              <th>Position</th>
              <th>Nationality</th>
              <th>Club</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((p) => (
              <tr
                key={p.player_id}
                onClick={() => onSelectPlayer(p.player_id)}
                className="border-t border-line cursor-pointer hover:bg-surface-2"
              >
                <td className="py-1.5">
                  {p.crest && <img src={p.crest} alt="" className="w-5 h-5 object-contain" />}
                </td>
                <td>{p.player_name}</td>
                <td>{p.position ?? '—'}</td>
                <td>{p.nationality ?? '—'}</td>
                <td>{p.team_name ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
