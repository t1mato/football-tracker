import { useQuery } from '@tanstack/react-query'

/** team_id (as a string key) -> hex color, extracted once from each
 * club's real crest by scripts/extract_club_colors.py and committed as
 * a static asset -- see that script for why this can't just be done
 * live in the browser (the crest CDN sends no CORS headers, so canvas
 * pixel reads are blocked).
 */
export type ClubColors = Record<string, string>

async function fetchClubColors(): Promise<ClubColors> {
  const response = await fetch('/club-colors.json')
  if (!response.ok) throw new Error(`GET club-colors.json failed: ${response.status}`)
  return response.json()
}

export function useClubColors() {
  return useQuery({
    queryKey: ['club-colors'],
    queryFn: fetchClubColors,
    staleTime: Infinity,
  })
}
