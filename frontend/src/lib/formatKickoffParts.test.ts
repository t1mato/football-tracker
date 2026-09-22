import { describe, expect, it } from 'vitest'
import { formatKickoffParts } from './formatKickoffParts'

describe('formatKickoffParts', () => {
  it('splits a confirmed kickoff into a 24-hour time and a short date', () => {
    const { time, date } = formatKickoffParts('2026-10-09T11:45:00', true)
    expect(time).toBe('11:45')
    expect(date).toBe('Oct 9')
  })

  it('returns a null time when the kickoff time is not yet confirmed', () => {
    const { time, date } = formatKickoffParts('2026-10-10T00:00:00', false)
    expect(time).toBeNull()
    expect(date).toBe('Oct 10')
  })

  it('pads a single-digit hour and minute', () => {
    const { time } = formatKickoffParts('2026-10-10T08:05:00', true)
    expect(time).toBe('08:05')
  })
})
