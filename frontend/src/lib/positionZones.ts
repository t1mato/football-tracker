export type ZoneColor = 'blue' | 'lightblue' | 'orange' | 'lightred' | 'red'

export interface Zone {
  from: number
  to: number
  color: ZoneColor
  label: string
}

const TWENTY_TEAM_LEAGUE: Zone[] = [
  { from: 1, to: 4, color: 'blue', label: 'Champions League' },
  { from: 5, to: 5, color: 'orange', label: 'Europa League' },
  { from: 18, to: 20, color: 'red', label: 'Relegation' },
]

// User-specified, league-specific -- not derivable from a generic rule
// (positions vary with league size and format), so these are exact
// per-competition tables rather than a computed formula.
const ZONES: Record<string, Zone[]> = {
  PL: TWENTY_TEAM_LEAGUE,
  SA: TWENTY_TEAM_LEAGUE,
  PD: TWENTY_TEAM_LEAGUE,
  BL1: [
    { from: 1, to: 4, color: 'blue', label: 'Champions League' },
    { from: 5, to: 5, color: 'orange', label: 'Europa League' },
    { from: 17, to: 18, color: 'red', label: 'Relegation' },
  ],
  FL1: [
    { from: 1, to: 3, color: 'blue', label: 'Champions League' },
    { from: 4, to: 4, color: 'lightblue', label: 'Champions League Qualifiers' },
    { from: 5, to: 6, color: 'orange', label: 'Europa League' },
    { from: 16, to: 16, color: 'lightred', label: 'Relegation Playoff' },
    { from: 17, to: 18, color: 'red', label: 'Relegation' },
  ],
}

/** Null for both an unconfigured competition (e.g. Champions League
 * itself, which has no domestic-style relegation/qualification zones)
 * and a position that falls in no zone for a configured one. */
export function getZoneForPosition(competitionCode: string, position: number): Zone | null {
  const zones = ZONES[competitionCode]
  if (!zones) return null
  return zones.find((z) => position >= z.from && position <= z.to) ?? null
}

export function zonesForCompetition(competitionCode: string): Zone[] {
  return ZONES[competitionCode] ?? []
}
