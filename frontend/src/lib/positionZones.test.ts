import { describe, expect, it } from 'vitest'
import { getZoneForPosition, zonesForCompetition } from './positionZones'

describe('getZoneForPosition', () => {
  it('marks 1-4 as Champions League and 18-20 as Relegation in a 20-team league (PL)', () => {
    expect(getZoneForPosition('PL', 1)?.label).toBe('Champions League')
    expect(getZoneForPosition('PL', 4)?.label).toBe('Champions League')
    expect(getZoneForPosition('PL', 5)?.label).toBe('Europa League')
    expect(getZoneForPosition('PL', 6)).toBeNull()
    expect(getZoneForPosition('PL', 17)).toBeNull()
    expect(getZoneForPosition('PL', 18)?.label).toBe('Relegation')
    expect(getZoneForPosition('PL', 20)?.label).toBe('Relegation')
  })

  it('applies the same 20-team rule to Serie A and La Liga', () => {
    expect(getZoneForPosition('SA', 4)?.color).toBe('blue')
    expect(getZoneForPosition('SA', 18)?.color).toBe('red')
    expect(getZoneForPosition('PD', 4)?.color).toBe('blue')
    expect(getZoneForPosition('PD', 18)?.color).toBe('red')
  })

  it('uses 17-18 for relegation in the 18-team Bundesliga, not 18-20', () => {
    expect(getZoneForPosition('BL1', 4)?.label).toBe('Champions League')
    expect(getZoneForPosition('BL1', 16)).toBeNull()
    expect(getZoneForPosition('BL1', 17)?.label).toBe('Relegation')
    expect(getZoneForPosition('BL1', 18)?.label).toBe('Relegation')
  })

  it('splits Ligue 1 into 5 distinct zones', () => {
    expect(getZoneForPosition('FL1', 3)?.label).toBe('Champions League')
    expect(getZoneForPosition('FL1', 4)?.label).toBe('Champions League Qualifiers')
    expect(getZoneForPosition('FL1', 5)?.label).toBe('Europa League')
    expect(getZoneForPosition('FL1', 6)?.label).toBe('Europa League')
    expect(getZoneForPosition('FL1', 15)).toBeNull()
    expect(getZoneForPosition('FL1', 16)?.label).toBe('Relegation Playoff')
    expect(getZoneForPosition('FL1', 17)?.label).toBe('Relegation')
    expect(getZoneForPosition('FL1', 18)?.label).toBe('Relegation')
  })

  it('returns null for a competition with no configured zones (e.g. Champions League itself)', () => {
    expect(getZoneForPosition('CL', 1)).toBeNull()
    expect(getZoneForPosition('CL', 30)).toBeNull()
  })
})

describe('zonesForCompetition', () => {
  it('returns 3 distinct zones for a 20-team league, in position order', () => {
    const zones = zonesForCompetition('PL')
    expect(zones.map((z) => z.label)).toEqual([
      'Champions League',
      'Europa League',
      'Relegation',
    ])
  })

  it('returns all 5 distinct zones for Ligue 1', () => {
    const zones = zonesForCompetition('FL1')
    expect(zones.map((z) => z.label)).toEqual([
      'Champions League',
      'Champions League Qualifiers',
      'Europa League',
      'Relegation Playoff',
      'Relegation',
    ])
  })

  it('returns an empty array for an unconfigured competition', () => {
    expect(zonesForCompetition('CL')).toEqual([])
  })
})
