import { useMemo, useState } from 'react'
import { usePlayersDirectory } from '../hooks/usePlayers'
import { ErrorMessage } from './ErrorMessage'

const PAGE_SIZE = 50

interface PlayerDirectoryTableProps {
  onSelectPlayer: (playerId: number) => void
}

export function PlayerDirectoryTable({ onSelectPlayer }: PlayerDirectoryTableProps) {
  const { data, isLoading, error } = usePlayersDirectory()
  const [search, setSearch] = useState('')
  const [club, setClub] = useState('All')
  const [page, setPage] = useState(1)

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

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const currentPage = Math.min(page, pageCount)
  const paged = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)

  if (isLoading) return <p>Loading...</p>
  if (error) return <ErrorMessage resource="players" />

  return (
    <div>
      <div className="flex gap-4 mb-5">
        <input
          type="text"
          placeholder="Search by name"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value)
            setPage(1)
          }}
          className="rounded-lg border border-line px-3 py-2 text-lg flex-1"
        />
        <select
          value={club}
          onChange={(e) => {
            setClub(e.target.value)
            setPage(1)
          }}
          className="rounded-lg border border-line px-3 py-2 text-lg"
        >
          {clubs.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>
      <p className="text-text-muted text-lg mb-3">{filtered.length} player(s)</p>
      {filtered.length === 0 ? (
        <p>No players match this search/filter.</p>
      ) : (
        <>
          <table className="w-full text-lg">
            <thead>
              <tr className="text-left text-text-muted text-base uppercase">
                <th className="pb-3"></th>
                <th className="pb-3">Player</th>
                <th className="pb-3">Position</th>
                <th className="pb-3">Nationality</th>
                <th className="pb-3">Club</th>
              </tr>
            </thead>
            <tbody>
              {paged.map((p) => (
                <tr
                  key={p.player_id}
                  onClick={() => onSelectPlayer(p.player_id)}
                  className="border-t border-line cursor-pointer hover:bg-surface-2"
                >
                  <td className="py-3">
                    {p.crest && <img src={p.crest} alt="" className="w-6 h-6 object-contain" />}
                  </td>
                  <td>{p.player_name}</td>
                  <td>{p.position ?? '—'}</td>
                  <td>{p.nationality ?? '—'}</td>
                  <td>{p.team_name ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {pageCount > 1 && (
            <div className="flex items-center justify-center gap-5 mt-6 text-lg">
              <button
                type="button"
                onClick={() => setPage((p) => p - 1)}
                disabled={currentPage === 1}
                className="rounded-lg border border-line px-4 py-2 font-medium disabled:opacity-40"
              >
                Previous
              </button>
              <span className="text-text-muted">
                Page {currentPage} of {pageCount}
              </span>
              <button
                type="button"
                onClick={() => setPage((p) => p + 1)}
                disabled={currentPage === pageCount}
                className="rounded-lg border border-line px-4 py-2 font-medium disabled:opacity-40"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
