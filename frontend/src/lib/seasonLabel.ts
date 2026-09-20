/** Mirrors app/formatting.py's season_label: a human-readable "2024/25"
 * label derived from a season's start/end dates -- season_id itself is
 * an opaque API-assigned integer with no calendar meaning to a reader.
 */
export function seasonLabel(startDate: string, endDate: string): string {
  const startYear = new Date(startDate).getFullYear()
  const endYear = new Date(endDate).getFullYear()
  return `${startYear}/${String(endYear).slice(-2)}`
}
