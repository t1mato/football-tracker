import { useMatchDetail } from '../hooks/useMatchDetail'
import { ErrorMessage } from './ErrorMessage'

interface MatchDetailPanelProps {
  matchId: number
}

export function MatchDetailPanel({ matchId }: MatchDetailPanelProps) {
  const { data, isLoading, error } = useMatchDetail(matchId)

  if (isLoading) return <p>Loading match detail...</p>
  if (error) return <ErrorMessage resource="match detail" />
  if (!data) return null

  return (
    <div className="mt-4 border-t border-line pt-4">
      <h3 className="font-semibold">Venue</h3>
      {data.venue_name ? (
        <p>{data.venue_name}</p>
      ) : (
        <p className="text-text-muted">Venue not available.</p>
      )}
    </div>
  )
}
