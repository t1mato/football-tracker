import { describe, expect, it } from 'vitest'
import { playerAge } from './playerAge'

describe('playerAge', () => {
  it('handles a datetime string with no offset (DuckDB-style serialization)', () => {
    const today = new Date(2026, 8, 15) // 2026-09-15 local

    expect(playerAge('2000-09-15T00:00:00', today)).toBe(26)
  })

  it('handles a bare date string (BigQuery-style serialization)', () => {
    const today = new Date(2026, 8, 15) // 2026-09-15 local

    expect(playerAge('2000-09-15', today)).toBe(26)
  })

  it('counts the birthday as already occurred when it falls exactly today', () => {
    const today = new Date(2026, 8, 15) // 2026-09-15
    const dob = '2000-09-15'

    expect(playerAge(dob, today)).toBe(26)
  })

  it('does not count a birthday still ahead later this calendar year', () => {
    // The exact bug case: naive (today - dob) / 365 over-reports by a year
    // when the birthday hasn't happened yet this year.
    const today = new Date(2026, 8, 15) // 2026-09-15
    const dob = '2000-09-18'

    expect(playerAge(dob, today)).toBe(25)
  })
})
