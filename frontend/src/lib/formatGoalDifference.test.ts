import { describe, expect, it } from 'vitest'
import { formatGoalDifference } from './formatGoalDifference'

describe('formatGoalDifference', () => {
  it('prefixes a positive value with +', () => {
    expect(formatGoalDifference(8)).toBe('+8')
  })

  it('leaves a negative value as-is (native minus sign)', () => {
    expect(formatGoalDifference(-3)).toBe('-3')
  })

  it('renders zero without a sign', () => {
    expect(formatGoalDifference(0)).toBe('0')
  })
})
