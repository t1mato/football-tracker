const COLORS: Record<string, string> = {
  W: 'bg-green',
  D: 'bg-yellow',
  L: 'bg-red',
}

interface ResultBadgeProps {
  result: string | null
}

export function ResultBadge({ result }: ResultBadgeProps) {
  if (!result) return null
  return (
    <span
      className={`inline-flex w-6 h-6 rounded items-center justify-center text-sm font-extrabold text-white ${COLORS[result] ?? 'bg-text-muted'}`}
    >
      {result}
    </span>
  )
}
