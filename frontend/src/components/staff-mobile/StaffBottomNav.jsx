/**
 * Fixed bottom navigation for staff dashboards (mobile only).
 */
import {
  Inbox,
  Package,
  ClipboardList,
  Handshake,
  Settings,
  LayoutList,
  UserCog,
  Coins,
} from 'lucide-react'

export const AUTHORITY_NAV = [
  { id: 'incoming', label: 'Incoming', Icon: Inbox },
  { id: 'at-droppoint', label: 'At Drop Point', Icon: Package },
  { id: 'claims', label: 'Claims', Icon: ClipboardList },
  { id: 'handover', label: 'Handover', Icon: Handshake },
  { id: 'settings', label: 'Settings', Icon: Settings },
]

export const SUPERVISOR_NAV = [
  { id: 'overview', label: 'Overview', Icon: LayoutList },
  { id: 'incoming', label: 'Incoming', Icon: Inbox },
  { id: 'at-droppoint', label: 'At DP', Icon: Package },
  { id: 'claims', label: 'Claims', Icon: ClipboardList },
  { id: 'handover', label: 'Handover', Icon: Handshake },
  { id: 'authorities', label: 'Staff', Icon: UserCog },
  { id: 'redemption', label: 'Redeem', Icon: Coins },
  { id: 'settings', label: 'Settings', Icon: Settings },
]

function NavBadge({ count }) {
  if (!count || count < 1) return null
  return (
    <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1
                     bg-red-600 text-white text-[10px] font-bold rounded-full
                     flex items-center justify-center leading-none">
      {count > 99 ? '99+' : count}
    </span>
  )
}

export default function StaffBottomNav({ items, activeId, onChange, badges = {}, scrollable = false }) {
  return (
    <nav
      className="md:hidden fixed bottom-0 inset-x-0 z-50 border-t border-slate-200 dark:border-slate-800
                 bg-white/95 dark:bg-slate-950/95 backdrop-blur-md
                 pb-[env(safe-area-inset-bottom)]"
      aria-label="Dashboard navigation"
    >
      <div className={`flex items-stretch ${scrollable ? 'overflow-x-auto justify-start' : 'justify-around'} h-16 max-w-lg mx-auto`}>
        {items.map(({ id, label, Icon }) => {
          const active = activeId === id
          return (
            <button
              key={id}
              type="button"
              onClick={() => onChange(id)}
              className={`relative flex flex-col items-center justify-center gap-0.5
                         min-h-[44px] min-w-[44px] px-2 transition-colors shrink-0
                         ${scrollable ? 'flex-none w-[4.25rem]' : 'flex-1'}
                         ${active ? 'text-brand-600 dark:text-brand-400' : 'text-slate-500'}`}
              aria-current={active ? 'page' : undefined}
            >
              <span className="relative">
                <Icon className="w-5 h-5" strokeWidth={active ? 2.25 : 1.75} aria-hidden />
                <NavBadge count={badges[id]} />
              </span>
              <span className="text-[10px] font-medium leading-tight text-center truncate w-full">
                {label}
              </span>
            </button>
          )
        })}
      </div>
    </nav>
  )
}
