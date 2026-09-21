/** Mirrors app/formatting.py's season_label: a human-readable "2024/25"
 * label derived from a season's start/end dates -- season_id itself is
 * an opaque API-assigned integer with no calendar meaning to a reader.
 *
 * Parses the YYYY-MM-DD prefix directly rather than via `new Date(string)`,
 * for the same reason playerAge.ts does -- see that file's comment.
 */
export function seasonLabel(startDate: string, endDate: string): string {
  const startYear = Number(startDate.slice(0, 4))
  const endYear = Number(endDate.slice(0, 4))
  return `${startYear}/${String(endYear).slice(-2)}`
}
