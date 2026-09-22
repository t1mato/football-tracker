import * as Dialog from '@radix-ui/react-dialog'
import * as Tabs from '@radix-ui/react-tabs'
import type { ReactNode } from 'react'

interface DetailDialogTab {
  value: string
  label: string
}

interface DetailDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  titleIcon?: string | null
  tabs: DetailDialogTab[]
  activeTab: string
  onTabChange: (value: string) => void
  headerExtra?: ReactNode
  children: ReactNode
}

/** Shared Dialog+Tabs chrome for every page-level detail dialog
 * (LeagueDetailDialog, TeamDetailDialog, and any future one). Owns only
 * the Radix wiring and the active-tab-switching mechanics -- zero
 * data-fetching, zero per-page logic. Season selectors, tab content, and
 * anything else page-specific are the caller's job, passed in as
 * `headerExtra`/`children`.
 */
export function DetailDialog({
  open,
  onOpenChange,
  title,
  titleIcon,
  tabs,
  activeTab,
  onTabChange,
  headerExtra,
  children,
}: DetailDialogProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/40" />
        <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-surface rounded-2xl shadow-card p-8 max-w-5xl w-full max-h-[90vh] overflow-y-auto">
          <div className="flex items-center gap-4">
            {titleIcon && <img src={titleIcon} alt="" className="w-12 h-12 object-contain" />}
            <Dialog.Title className="font-display text-4xl uppercase">{title}</Dialog.Title>
          </div>
          {headerExtra}
          <Tabs.Root value={activeTab} onValueChange={onTabChange} className="mt-6">
            <Tabs.List className="flex gap-6 border-b border-line">
              {tabs.map((tab) => (
                <Tabs.Trigger
                  key={tab.value}
                  value={tab.value}
                  className="pb-3 font-bold text-lg text-text-muted border-b-2 border-transparent data-[state=active]:text-blue data-[state=active]:border-blue"
                >
                  {tab.label}
                </Tabs.Trigger>
              ))}
            </Tabs.List>
            {children}
          </Tabs.Root>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
