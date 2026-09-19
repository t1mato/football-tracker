/** Mirrors app/formatting.py's format_kickoff: shows "date (time TBD)" when
 * the warehouse hasn't confirmed an exact kickoff time yet, instead of
 * inventing a precise time that isn't real.
 */
export function formatKickoff(kickoffUtc: string, kickoffTimeConfirmed: boolean): string {
  const date = new Date(kickoffUtc)
  if (!kickoffTimeConfirmed) {
    return `${date.toLocaleDateString()} (time TBD)`
  }
  return date.toLocaleString()
}
