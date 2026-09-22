import type { ReactNode } from 'react'

interface FrameProps {
  children: ReactNode
  className?: string
}

/** Shared "content sits in a soft-shadowed white panel" treatment used
 * for every card grid / table block on a page -- the visual signature
 * of the mockup this app is styled after. */
export function Frame({ children, className = '' }: FrameProps) {
  return (
    <div
      className={`bg-surface border border-line rounded-2xl shadow-card p-7 ${className}`}
    >
      {children}
    </div>
  )
}
