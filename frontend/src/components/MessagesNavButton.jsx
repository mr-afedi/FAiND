/**
 * Mobile top-bar messages icon — claim inquiry / handover updates (V5 Section 13).
 */
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { MessageCircle } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { getMyNotifications } from '../services/matchService'
import { getAwaitingConfirmation } from '../services/claimService'

const CLAIM_STATUS_PREFIX = '/claims/status/'

export default function MessagesNavButton() {
  const { isAuthenticated, authReady } = useAuth()
  const navigate = useNavigate()

  const enabled = isAuthenticated && authReady

  const { data: notifData } = useQuery({
    queryKey: ['notifications-unread'],
    queryFn: () => getMyNotifications({ limit: 30 }),
    enabled,
    staleTime: 30_000,
    refetchInterval: 60_000,
  })

  const { data: awaitingData } = useQuery({
    queryKey: ['awaiting-confirmation'],
    queryFn: getAwaitingConfirmation,
    enabled,
    staleTime: 30_000,
    refetchInterval: 60_000,
  })

  if (!enabled) return null

  const claimReplyUnread = (notifData?.notifications ?? []).filter(
    (n) => !n.read && n.link?.startsWith(CLAIM_STATUS_PREFIX)
  ).length
  const awaitingCount = awaitingData?.items?.length ?? 0
  const badgeCount = claimReplyUnread + awaitingCount

  function handleClick() {
    const unreadClaim = (notifData?.notifications ?? []).find(
      (n) => !n.read && n.link?.startsWith(CLAIM_STATUS_PREFIX)
    )
    if (unreadClaim?.link) {
      navigate(unreadClaim.link)
      return
    }
    const firstAwaiting = awaitingData?.items?.[0]
    if (firstAwaiting?.claim_id) {
      navigate(`${CLAIM_STATUS_PREFIX}${firstAwaiting.claim_id}`)
      return
    }
    const anyClaim = (notifData?.notifications ?? []).find((n) =>
      n.link?.startsWith(CLAIM_STATUS_PREFIX)
    )
    if (anyClaim?.link) {
      navigate(anyClaim.link)
    }
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      className="relative w-10 h-10 rounded-xl flex items-center justify-center
                 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
      aria-label="Claim messages"
    >
      <MessageCircle className="w-5 h-5" strokeWidth={1.75} aria-hidden />
      {badgeCount > 0 && (
        <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1
                         bg-red-500 text-white text-[10px] font-bold
                         rounded-full flex items-center justify-center leading-none">
          {badgeCount > 9 ? '9+' : badgeCount}
        </span>
      )}
    </button>
  )
}
