/** Splits a kickoff into the separate time/date pieces a fixture card
 * needs (clock row + date row), instead of formatKickoff's single
 * combined string. Time is null when the exact kickoff hasn't been
 * confirmed yet -- same "don't invent a precise time" rule as
 * formatKickoff, just surfaced as a value the caller can branch on
 * instead of baked into a "(time TBD)" suffix.
 */
export function formatKickoffParts(
  kickoffUtc: string,
  kickoffTimeConfirmed: boolean
): { time: string | null; date: string } {
  const parsed = new Date(kickoffUtc)
  const date = parsed.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  if (!kickoffTimeConfirmed) return { time: null, date }
  const time = parsed.toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
  return { time, date }
}
