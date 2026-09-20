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
        <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-surface rounded-xl p-6 max-w-3xl w-full max-h-[85vh] overflow-y-auto">
          <Dialog.Title className="font-display text-3xl uppercase">{title}</Dialog.Title>
          {headerExtra}
          <Tabs.Root value={activeTab} onValueChange={onTabChange} className="mt-4">
            <Tabs.List className="flex gap-4 border-b border-line">
              {tabs.map((tab) => (
                <Tabs.Trigger key={tab.value} value={tab.value} className="pb-2">
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
