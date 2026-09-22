export function formatGoalDifference(goalDifference: number): string {
  return goalDifference > 0 ? `+${goalDifference}` : String(goalDifference)
}
