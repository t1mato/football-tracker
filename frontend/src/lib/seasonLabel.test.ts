import { describe, expect, it } from 'vitest'
import { seasonLabel } from './seasonLabel'

describe('seasonLabel', () => {
  it('formats a normal calendar-year season from datetime strings with no offset', () => {
    expect(seasonLabel('2024-08-16T00:00:00', '2025-05-25T00:00:00')).toBe('2024/25')
  })

  it('formats a normal calendar-year season from bare date strings', () => {
    expect(seasonLabel('2024-08-16', '2025-05-25')).toBe('2024/25')
  })

  it('pads a single-digit end year', () => {
    // str(2009)[-2:] is "09", not "9" -- confirm the slicing genuinely
    // zero-pads rather than happening to look right only for the
    // two-digit years this project's real data currently has.
    expect(seasonLabel('2008-08-01', '2009-05-01')).toBe('2008/09')
  })
})
