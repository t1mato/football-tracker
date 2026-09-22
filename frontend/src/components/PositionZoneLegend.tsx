import { zonesForCompetition, type ZoneColor } from '../lib/positionZones'

const DOT_CLASSES: Record<ZoneColor, string> = {
  blue: 'bg-blue',
  lightblue: 'bg-blue/50',
  orange: 'bg-orange',
  lightred: 'bg-red/50',
  red: 'bg-red',
}

interface PositionZoneLegendProps {
  competitionCode: string
}

export function PositionZoneLegend({ competitionCode }: PositionZoneLegendProps) {
  const zones = zonesForCompetition(competitionCode)
  if (zones.length === 0) return null

  return (
    <div className="flex flex-wrap gap-x-6 gap-y-2 mt-6 pt-4 border-t border-line text-base text-text-muted">
      {zones.map((zone) => (
        <span key={zone.label} className="flex items-center gap-2">
          <span className={`w-3 h-3 rounded-full ${DOT_CLASSES[zone.color]}`} />
          {zone.label}
        </span>
      ))}
    </div>
  )
}
