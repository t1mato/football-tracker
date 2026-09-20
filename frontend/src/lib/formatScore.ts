/** Mirrors app/formatting.py's format_score: empty string when either
 * side is null (a scheduled match, or a rare AWARDED match recorded with
 * no goals), instead of rendering "null-null" or similar.
 */
export function formatScore(
  fullTimeHome: number | null,
  fullTimeAway: number | null
): string {
  if (fullTimeHome === null || fullTimeAway === null) return ''
  return `${fullTimeHome}-${fullTimeAway}`
}
