import { useMatchDetail } from '../hooks/useMatchDetail'
import { ErrorMessage } from './ErrorMessage'

interface MatchDetailPanelProps {
  matchId: number
}

function formatWeather(
  temp: number | null,
  precip: number | null,
  wind: number | null,
  dataType: string | null
): string {
  if (temp === null || dataType === null) return 'No weather data available yet.'
  return `${temp}°C, ${precip ?? 0}mm precipitation, ${wind}km/h wind (${dataType})`
}

export function MatchDetailPanel({ matchId }: MatchDetailPanelProps) {
  const { data, isLoading, error } = useMatchDetail(matchId)

  if (isLoading) return <p>Loading match detail...</p>
  if (error) return <ErrorMessage resource="match detail" />
  if (!data) return null

  return (
    <div className="mt-4 border-t border-line pt-4">
      <h3 className="font-semibold">Venue</h3>
      {data.venue_needs_review || !data.venue_display_name ? (
        <p className="text-text-muted">Venue location not yet resolved.</p>
      ) : (
        <>
          <p>{data.venue_display_name}</p>
          {data.capacity !== null && <p>Capacity: {data.capacity.toLocaleString()}</p>}
        </>
      )}
      <h3 className="font-semibold mt-3">Weather</h3>
      <p>{formatWeather(data.temperature_2m, data.precipitation, data.wind_speed_10m, data.weather_data_type)}</p>
    </div>
  )
}
