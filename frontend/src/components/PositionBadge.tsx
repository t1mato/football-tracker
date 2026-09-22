import { getZoneForPosition, type ZoneColor } from '../lib/positionZones'

const COLOR_CLASSES: Record<ZoneColor, string> = {
  blue: 'bg-blue text-white',
  lightblue: 'bg-blue/50 text-white',
  orange: 'bg-orange text-white',
  lightred: 'bg-red/50 text-white',
  red: 'bg-red text-white',
}

interface PositionBadgeProps {
  competitionCode: string
  position: number
}

export function PositionBadge({ competitionCode, position }: PositionBadgeProps) {
  const zone = getZoneForPosition(competitionCode, position)
  const colorClasses = zone ? COLOR_CLASSES[zone.color] : 'bg-surface-2 text-text-muted'
  return (
    <span
      className={`inline-flex w-7 h-7 rounded-full items-center justify-center text-base font-bold ${colorClasses}`}
    >
      {position}
    </span>
  )
}
