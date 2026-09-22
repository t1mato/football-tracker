const COLORS: Record<string, string> = {
  W: 'bg-green',
  D: 'bg-yellow',
  L: 'bg-red',
}

interface FormGuideProps {
  form: string | null
}

/** Renders mart_team_form.last_5_results ("WDLWW", oldest-to-newest left
 * to right) as small colored dots -- the Form column on a standings
 * table. Null means the mart has no row yet for this team (fewer than 5
 * played matches), not an error. */
export function FormGuide({ form }: FormGuideProps) {
  if (!form) return <span className="text-text-muted">—</span>
  return (
    <div className="flex gap-1.5 justify-center">
      {form.split('').map((result, i) => (
        <span
          key={i}
          className={`w-5 h-5 rounded-full flex items-center justify-center text-[0.65rem] font-extrabold text-white ${COLORS[result] ?? 'bg-text-muted'}`}
        >
          {result}
        </span>
      ))}
    </div>
  )
}
