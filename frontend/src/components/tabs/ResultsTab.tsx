import { useResults } from '../../hooks/useResults'

interface ResultsTabProps {
  competitionCode: string
  seasonId: number | undefined
  active: boolean
}

// Deliberately minimal stub. Task 6's own test suite requires proof that
// switching tabs lazily fetches the newly-active tab's data (not just that
// the initial tab fetches on mount), so this wires the `useResults` query
// with the same `enabled: active` lazy pattern `StandingsTab` establishes.
// Task 7 replaces this file's body with the full Recent Results rendering;
// the hook and the lazy-fetch wiring below are meant to carry over as-is.
export function ResultsTab({ competitionCode, seasonId, active }: ResultsTabProps) {
  const { isLoading } = useResults(competitionCode, seasonId, active)

  if (!active) return null
  if (isLoading) return <p>Loading...</p>

  return <p>Recent results coming soon.</p>
}
