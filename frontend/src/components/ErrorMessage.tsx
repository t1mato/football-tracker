interface ErrorMessageProps {
  resource: string
}

/** Shared "the request actually failed" message, distinct from the various
 * "no data yet" empty states -- so a real 500 doesn't masquerade as an
 * empty competition/season.
 */
export function ErrorMessage({ resource }: ErrorMessageProps) {
  return <p>Couldn't load {resource}.</p>
}
