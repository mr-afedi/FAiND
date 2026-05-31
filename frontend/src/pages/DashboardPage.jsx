import { useState, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { userService } from '../services/userService'
import { getMyLostItems, deleteItem, extendItem,
         getMyFoundItems, deleteFoundItem, extendFoundItem } from '../services/itemService'
import NavBar from '../components/NavBar'
import { getMyMatches } from '../services/matchService'
import { listMyReturns } from '../services/returnService'
import { invalidateAfterItemChange } from '../utils/queryCache'
import {
  TRUST_EVENT_META,
  TrustEventIcon,
  CategoryIcon,
  getCategoryLabel,
  EmptyInboxIcon,
  MapPin,
  Bot,
  Star,
  ClipboardList,
  Check,
  CircleDollarSign,
  Package,
} from '../components/icons'

function formatRelativeTime(iso) {
  const diff = Math.floor((Date.now() - new Date(iso)) / 1000)
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  if (diff < 2592000) return `${Math.floor(diff / 86400)}d ago`
  return new Date(iso).toLocaleDateString()
}

// ── Trust event feed ──────────────────────────────────────────────────────────

function TrustEventFeed({ events }) {
  if (!events?.length) return null
  return (
    <div className="mt-4 glass p-4">
      <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
        Recent Trust Activity
      </h3>
      <ul className="flex flex-col gap-2">
        {events.map((ev) => {
          const meta = TRUST_EVENT_META[ev.reason] ?? { label: ev.reason, Icon: Package }
          const positive = ev.delta > 0
          return (
            <li key={ev.id} className="flex items-center justify-between gap-3
                                       text-sm py-1.5 border-b border-slate-100 dark:border-slate-700/60
                                       last:border-0">
              <span className="flex items-center gap-2 min-w-0">
                <TrustEventIcon reason={ev.reason} />
                <span className="text-slate-700 dark:text-slate-300 truncate">{meta.label}</span>
              </span>
              <span className="flex items-center gap-2 flex-shrink-0 text-xs text-slate-400">
                <span>{formatRelativeTime(ev.created_at)}</span>
                <span className={`font-semibold text-sm ${positive
                  ? 'text-green-600 dark:text-green-400'
                  : 'text-red-500 dark:text-red-400'}`}>
                  {positive ? '+' : ''}{ev.delta}
                </span>
              </span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

// ── Trust tier helpers ────────────────────────────────────────────────────────

function tierClass(tier) {
  switch (tier) {
    case 'Community Champion': return 'tier-champion'
    case 'Reliable Member':    return 'tier-reliable'
    case 'Trusted Member':     return 'tier-trusted'
    default:                   return 'tier-new'
  }
}

// ── Overview stat card ────────────────────────────────────────────────────────

function StatCard({ label, value, icon, sub }) {
  return (
    <div className="stat-card">
      <div className="flex items-start justify-between">
        <span className="text-2xl font-bold text-slate-800 dark:text-slate-100">{value}</span>
        <span className="text-slate-500 dark:text-slate-400">{icon}</span>
      </div>
      <p className="text-sm font-medium text-slate-600 dark:text-slate-400">{label}</p>
      {sub && <p className="text-xs text-slate-400 dark:text-slate-600 mt-0.5">{sub}</p>}
    </div>
  )
}

// ── Empty state ───────────────────────────────────────────────────────────────

function EmptyTab({ message, cta, ctaTo }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-4 text-center">
      <div className="w-16 h-16 rounded-2xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
        <EmptyInboxIcon className="w-8 h-8 text-slate-400" />
      </div>
      <p className="text-slate-500 dark:text-slate-400 text-sm max-w-xs">{message}</p>
      {cta && (
        <Link to={ctaTo} className="btn-primary text-sm">{cta}</Link>
      )}
    </div>
  )
}

const STATUS_CLASSES = {
  open:               'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  potential_match:    'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  under_verification: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  under_dispute:      'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  returned:           'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400',
  expired:            'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
  archived:           'bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500',
  closed:             'bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500',
}

function formatStatus(s) {
  return s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function daysLeft(expiryDate) {
  const diff = Math.ceil((new Date(expiryDate) - new Date()) / (1000 * 60 * 60 * 24))
  return diff
}

// ── Lost item row ─────────────────────────────────────────────────────────────

function LostItemRow({ item, onDelete, onExtend, deleting, extending }) {
  const days = daysLeft(item.expiry_date)
  const expiringSoon = days > 0 && days <= 3

  return (
    <div className="flex flex-col sm:flex-row gap-3 p-4 rounded-xl
                    border border-slate-200 dark:border-slate-700
                    bg-white dark:bg-slate-800/50 hover:shadow-sm transition-shadow">
      {/* Thumbnail — shows first image; badge if there are 2 */}
      <div className="relative flex-shrink-0">
        {item.image_urls?.[0] ? (
          <img
            src={item.image_urls[0]}
            alt="item"
            className="w-16 h-16 rounded-xl object-cover"
          />
        ) : (
          <div className="w-16 h-16 rounded-xl bg-slate-100 dark:bg-slate-700
                          flex items-center justify-center text-slate-400">
            <CategoryIcon category={item.category} className="w-7 h-7" />
          </div>
        )}
        {item.image_urls?.length > 1 && (
          <span className="absolute -bottom-1 -right-1 bg-slate-700 text-white
                           text-[10px] font-bold px-1.5 py-0.5 rounded-full leading-none">
            +{item.image_urls.length - 1}
          </span>
        )}
      </div>

      {/* Details */}
      <div className="flex-1 min-w-0">
        <div className="flex flex-wrap items-center gap-2 mb-1">
          <span className="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">
            {getCategoryLabel(item.category)}
          </span>
          <span className={`inline-flex px-2 py-0.5 rounded-lg text-xs font-medium ${STATUS_CLASSES[item.status] ?? ''}`}>
            {formatStatus(item.status)}
          </span>
          {expiringSoon && (
            <span className="inline-flex px-2 py-0.5 rounded-lg text-xs font-medium bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400">
              Expires in {days}d
            </span>
          )}
          {days <= 0 && (
            <span className="inline-flex px-2 py-0.5 rounded-lg text-xs font-medium bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400">
              Expired
            </span>
          )}
        </div>
        <p className="text-xs text-slate-600 dark:text-slate-400 line-clamp-2">
          {item.public_description}
        </p>
        <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
          {item.location_label} · Lost {new Date(item.date_occurred).toLocaleDateString()}
        </p>
      </div>

      {/* Actions */}
      <div className="flex gap-2 items-center flex-shrink-0">
        {item.status === 'open' && item.extensions_used < 2 && expiringSoon && (
          <button
            onClick={() => onExtend(item.id)}
            disabled={extending}
            className="btn-secondary text-xs py-1.5 px-3"
          >
            {extending ? '…' : 'Extend'}
          </button>
        )}
        <button
          onClick={() => onDelete(item.id)}
          disabled={deleting}
          className="text-xs px-3 py-1.5 rounded-lg border border-red-200 text-red-600
                     hover:bg-red-50 dark:border-red-800 dark:text-red-400
                     dark:hover:bg-red-900/20 transition-colors disabled:opacity-50"
        >
          {deleting ? '…' : 'Remove'}
        </button>
      </div>
    </div>
  )
}

// ── Found item row ────────────────────────────────────────────────────────────

function FoundItemRow({ item, onDelete, onExtend, deleting, extending }) {
  const days = daysLeft(item.expiry_date)
  const expiringSoon = days > 0 && days <= 3

  return (
    <div className="flex flex-col sm:flex-row gap-3 p-4 rounded-xl
                    border border-slate-200 dark:border-slate-700
                    bg-white dark:bg-slate-800/50 hover:shadow-sm transition-shadow">
      {/* Thumbnail */}
      <div className="relative flex-shrink-0">
        {item.image_urls?.[0] ? (
          <img src={item.image_urls[0]} alt="item"
               className="w-16 h-16 rounded-xl object-cover" />
        ) : (
          <div className="w-16 h-16 rounded-xl bg-slate-100 dark:bg-slate-700
                          flex items-center justify-center text-slate-400">
            <CategoryIcon category={item.category} className="w-7 h-7" />
          </div>
        )}
        {item.image_urls?.length > 1 && (
          <span className="absolute -bottom-1 -right-1 bg-slate-700 text-white
                           text-[10px] font-bold px-1.5 py-0.5 rounded-full leading-none">
            +{item.image_urls.length - 1}
          </span>
        )}
      </div>

      {/* Details */}
      <div className="flex-1 min-w-0">
        <div className="flex flex-wrap items-center gap-2 mb-1">
          <span className="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">
            {getCategoryLabel(item.category)}
          </span>
          <span className={`inline-flex px-2 py-0.5 rounded-lg text-xs font-medium ${STATUS_CLASSES[item.status] ?? ''}`}>
            {formatStatus(item.status)}
          </span>
          {expiringSoon && (
            <span className="inline-flex px-2 py-0.5 rounded-lg text-xs font-medium
                             bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400">
              Expires in {days}d
            </span>
          )}
          {days <= 0 && (
            <span className="inline-flex px-2 py-0.5 rounded-lg text-xs font-medium
                             bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400">
              Expired
            </span>
          )}
        </div>
        <p className="text-xs text-slate-600 dark:text-slate-400 line-clamp-2">
          {item.public_description}
        </p>
        <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
          {item.location_label} · Found {new Date(item.date_occurred).toLocaleDateString()}
        </p>
      </div>

      {/* Actions */}
      <div className="flex gap-2 items-center flex-shrink-0">
        {item.status === 'found' && item.extensions_used < 2 && expiringSoon && (
          <button onClick={() => onExtend(item.id)} disabled={extending}
                  className="btn-secondary text-xs py-1.5 px-3">
            {extending ? '…' : 'Extend'}
          </button>
        )}
        <button onClick={() => onDelete(item.id)} disabled={deleting}
                className="text-xs px-3 py-1.5 rounded-lg border border-red-200 text-red-600
                           hover:bg-red-50 dark:border-red-800 dark:text-red-400
                           dark:hover:bg-red-900/20 transition-colors disabled:opacity-50">
          {deleting ? '…' : 'Remove'}
        </button>
      </div>
    </div>
  )
}

// ── Potential match row (Feature G — Path A) ──────────────────────────────────

function MatchRow({ match }) {
  const pct = Math.round(match.match_score * 100)
  const isLostOwner = match.user_role === 'lost_owner'
  const other = isLostOwner ? match.found_item : match.lost_item
  const mine  = isLostOwner ? match.lost_item  : match.found_item
  const status = match.status

  return (
    <div className="p-4 rounded-xl border border-violet-200/70 dark:border-violet-800/50
                    bg-violet-50/50 dark:bg-violet-900/10 flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <span className="text-sm font-bold text-violet-700 dark:text-violet-300 inline-flex items-center gap-1.5">
          <Bot className="w-4 h-4 shrink-0" aria-hidden />
          AI Match — {pct}% confidence
        </span>
        <div className="flex items-center gap-2">
          {status === 'verified' && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700
                             dark:bg-green-900/40 dark:text-green-300">
              Chat unlocked
            </span>
          )}
          {status === 'pending_review' && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-700
                             dark:bg-amber-900/40 dark:text-amber-300">
              Admin review
            </span>
          )}
          <span className="text-xs px-2 py-0.5 rounded-full bg-violet-100 text-violet-700
                           dark:bg-violet-900/40 dark:text-violet-300">
            {isLostOwner ? 'You reported lost' : 'You reported found'}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
        <div className="p-3 rounded-lg bg-white dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-700/50">
          <p className="text-xs text-slate-400 mb-1">Your item</p>
          <p className="font-medium text-slate-700 dark:text-slate-200 line-clamp-2 flex items-start gap-1.5">
            <CategoryIcon category={mine.category} className="w-4 h-4 mt-0.5 shrink-0" />
            <span className="line-clamp-2">{mine.public_description}</span>
          </p>
          <p className="text-xs text-slate-400 mt-1 inline-flex items-center gap-1">
            <MapPin className="w-3 h-3 shrink-0" aria-hidden />
            {mine.location_label}
          </p>
          <Link to={`/items/${mine.id}`} className="text-xs text-brand-600 dark:text-brand-400 hover:underline mt-1 inline-block">
            View your post →
          </Link>
        </div>
        <div className="p-3 rounded-lg bg-white dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-700/50">
          <p className="text-xs text-slate-400 mb-1">Matched with</p>
          <p className="font-medium text-slate-700 dark:text-slate-200 line-clamp-2 flex items-start gap-1.5">
            <CategoryIcon category={other.category} className="w-4 h-4 mt-0.5 shrink-0" />
            <span className="line-clamp-2">{other.public_description}</span>
          </p>
          <p className="text-xs text-slate-400 mt-1 inline-flex items-center gap-1">
            <MapPin className="w-3 h-3 shrink-0" aria-hidden />
            {other.location_label}
          </p>
          <Link to={`/items/${other.id}`} className="text-xs text-brand-600 dark:text-brand-400 hover:underline mt-1 inline-block">
            View matched post →
          </Link>
        </div>
      </div>

      {isLostOwner && status === 'active' && (
        <Link
          to={`/verify-ownership/${match.id}`}
          className="btn-primary text-sm py-2 w-full sm:w-auto text-center"
        >
          Verify Ownership
        </Link>
      )}
      {isLostOwner && status === 'pending_review' && (
        <p className="text-xs text-amber-600 dark:text-amber-400">
          Your verification is under admin review. We&apos;ll notify you when decided.
        </p>
      )}
      {status === 'verified' && match.conversation_id && (
        <div className="flex flex-col sm:flex-row gap-2">
          <Link
            to={`/returns/confirm/${match.id}`}
            className="btn-primary text-sm py-2 w-full sm:w-auto text-center"
          >
            Confirm Return
          </Link>
          <Link
            to={`/messages/${match.conversation_id}`}
            className="btn-secondary text-sm py-2 w-full sm:w-auto text-center"
          >
            Open Chat
          </Link>
        </div>
      )}
      {!isLostOwner && status === 'active' && (
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Waiting for the lost item owner to verify ownership. You&apos;ll be notified when chat unlocks.
        </p>
      )}
    </div>
  )
}

// ── Returned tab row (Section 16.8) ───────────────────────────────────────────

function ReturnedRow({ row }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-3 p-4 rounded-xl
                    border border-slate-200/60 dark:border-slate-700/50 bg-white/50 dark:bg-slate-900/30">
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-slate-800 dark:text-slate-100 truncate">
          {row.item_label}
        </p>
        <p className="text-xs text-slate-500 mt-0.5">
          {new Date(row.returned_at).toLocaleDateString()}
          {' · '}
          {row.is_owner ? (
            <>
              Finder: {row.other_user_display_name} ({row.other_user_trust_tier})
              {row.appreciation_sent ? ' · Tip sent' : ''}
            </>
          ) : (
            <>
              Returned to owner
              {row.appreciation_received ? ' · Appreciated' : ''}
            </>
          )}
          {row.dispute_active ? ' · Under dispute' : ''}
        </p>
      </div>
      <Link
        to={`/returns/${row.return_id}`}
        className="btn-secondary text-sm py-2 px-4 text-center shrink-0"
      >
        View Details
      </Link>
    </div>
  )
}

// ── Tab definitions ───────────────────────────────────────────────────────────

const TABS = [
  { id: 'lost',     label: 'Lost Items' },
  { id: 'found',    label: 'Found Items' },
  { id: 'returned', label: 'Returned' },
  { id: 'pending',  label: 'Pending' },
]

// ── Main component ────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [searchParams] = useSearchParams()
  const [activeTab, setActiveTab] = useState('lost')
  const [deletingId, setDeletingId]         = useState(null)
  const [extendingId, setExtendingId]       = useState(null)
  const [deletingFoundId, setDeletingFoundId]   = useState(null)
  const [extendingFoundId, setExtendingFoundId] = useState(null)
  const queryClient = useQueryClient()

  const { data: profile, isLoading, isError } = useQuery({
    queryKey: ['me'],
    queryFn: userService.getMe,
  })

  const { data: lostData, isLoading: lostLoading } = useQuery({
    queryKey: ['my-lost-items'],
    queryFn: () => getMyLostItems({ skip: 0, limit: 50 }),
  })

  const { data: foundData, isLoading: foundLoading } = useQuery({
    queryKey: ['my-found-items'],
    queryFn: () => getMyFoundItems({ skip: 0, limit: 50 }),
  })

  const { data: trustHistory } = useQuery({
    queryKey: ['my-trust-events'],
    queryFn: () => userService.getMyTrustHistory({ limit: 5 }),
  })

  const { data: matchData, isLoading: matchesLoading } = useQuery({
    queryKey: ['my-matches'],
    queryFn: getMyMatches,
  })

  const { data: returnsData, isLoading: returnsLoading } = useQuery({
    queryKey: ['my-returns'],
    queryFn: listMyReturns,
  })

  useEffect(() => {
    const tab = searchParams.get('tab')
    if (tab === 'pending' || tab === 'returned') setActiveTab(tab)
  }, [searchParams])

  const deleteMutation = useMutation({
    mutationFn: deleteItem,
    onSuccess: (_data, itemId) => {
      invalidateAfterItemChange(queryClient, itemId)
      toast.success('Item removed')
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to remove item'),
    onSettled: () => setDeletingId(null),
  })

  const extendMutation = useMutation({
    mutationFn: extendItem,
    onSuccess: (_data, itemId) => {
      invalidateAfterItemChange(queryClient, itemId)
      toast.success('Expiry extended by 30 days')
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to extend item'),
    onSettled: () => setExtendingId(null),
  })

  function handleDelete(itemId) {
    if (!confirm('Remove this item? It will be archived and hidden from the feed.')) return
    setDeletingId(itemId)
    deleteMutation.mutate(itemId)
  }

  function handleExtend(itemId) {
    setExtendingId(itemId)
    extendMutation.mutate(itemId)
  }

  const deleteFoundMutation = useMutation({
    mutationFn: deleteFoundItem,
    onSuccess: (_data, itemId) => {
      invalidateAfterItemChange(queryClient, itemId)
      toast.success('Item removed')
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to remove item'),
    onSettled: () => setDeletingFoundId(null),
  })

  const extendFoundMutation = useMutation({
    mutationFn: extendFoundItem,
    onSuccess: (_data, itemId) => {
      invalidateAfterItemChange(queryClient, itemId)
      toast.success('Expiry extended by 30 days')
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to extend item'),
    onSettled: () => setExtendingFoundId(null),
  })

  function handleDeleteFound(itemId) {
    if (!confirm('Remove this found item? It will be archived.')) return
    setDeletingFoundId(itemId)
    deleteFoundMutation.mutate(itemId)
  }

  function handleExtendFound(itemId) {
    setExtendingFoundId(itemId)
    extendFoundMutation.mutate(itemId)
  }

  if (isLoading) {
    return (
      <>
        <NavBar />
        <div className="page-container py-10 flex items-center justify-center min-h-[60vh]">
          <div className="w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
        </div>
      </>
    )
  }

  if (isError || !profile) {
    return (
      <>
        <NavBar />
        <div className="page-container py-10 text-center text-slate-500">
          Could not load profile. Please try refreshing.
        </div>
      </>
    )
  }

  const initials = profile.full_name
    ? profile.full_name.split(' ').map((n) => n[0]).slice(0, 2).join('').toUpperCase()
    : profile.username[0].toUpperCase()

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 transition-colors duration-200">
      <NavBar />

      <div className="page-container py-8 max-w-5xl">
        {/* ── Profile header ── */}
        <div className="glass p-6 mb-6 flex flex-col sm:flex-row items-start sm:items-center gap-4">
          {profile.profile_photo_url ? (
            <img
              src={profile.profile_photo_url}
              alt={profile.username}
              className="w-16 h-16 rounded-2xl object-cover flex-shrink-0"
            />
          ) : (
            <div className="w-16 h-16 rounded-2xl bg-brand-600 flex items-center justify-center
                            text-white text-xl font-bold flex-shrink-0">
              {initials}
            </div>
          )}

          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100 truncate">
                {profile.full_name}
              </h1>
              <span className={tierClass(profile.trust_tier)}>{profile.trust_tier}</span>
            </div>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
              @{profile.username} · {profile.university_short_name} · Member since {profile.member_since}
            </p>
          </div>

          <Link to="/settings" className="btn-secondary text-sm flex-shrink-0">
            Edit Profile
          </Link>
        </div>

        {/* ── Overview cards (Section 25.1) ── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-2">
          <StatCard
            label="Trust Score"
            value={trustHistory?.trust_score ?? profile.trust_score}
            icon={<Star className="w-6 h-6" aria-hidden />}
            sub={trustHistory?.tier ?? profile.trust_tier}
          />
          <StatCard
            label="Items Posted"
            value={(lostData?.total ?? 0) + (foundData?.total ?? 0)}
            icon={<ClipboardList className="w-6 h-6" aria-hidden />}
            sub={`${lostData?.total ?? 0} lost · ${foundData?.total ?? 0} found`}
          />
          <StatCard
            label="Items Returned"
            value={returnsData?.items?.length ?? 0}
            icon={<Check className="w-6 h-6" aria-hidden />}
            sub="All time"
          />
          <StatCard
            label="Tips Received"
            value={0}
            icon={<CircleDollarSign className="w-6 h-6" aria-hidden />}
            sub="Count only"
          />
        </div>

        {/* ── Trust event feed (Section 17.2 — own dashboard: raw score) ── */}
        <TrustEventFeed events={trustHistory?.events} />

        {/* spacer */}
        <div className="mb-4" />

        {/* ── Tabs (Section 25.2) ── */}
        <div className="glass overflow-hidden">
          {/* Tab bar */}
          <div className="flex gap-1 p-2 border-b border-slate-200/50 dark:border-slate-700/50 overflow-x-auto">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`tab-btn whitespace-nowrap relative ${activeTab === tab.id ? 'active' : ''}`}
              >
                {tab.label}
                {tab.id === 'pending' && (matchData?.total ?? 0) > 0 && (
                  <span className="ml-1.5 inline-flex items-center justify-center min-w-[18px] h-[18px]
                                   px-1 text-[10px] font-bold rounded-full bg-violet-500 text-white">
                    {matchData.total}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="p-4">
            {activeTab === 'lost' && (
              lostLoading ? (
                <div className="flex justify-center py-16">
                  <div className="w-7 h-7 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
                </div>
              ) : !lostData?.items?.length ? (
                <EmptyTab
                  message="You haven't reported any lost items yet. Post a lost item and the community will help."
                  cta="Report Lost Item"
                  ctaTo="/report/lost"
                />
              ) : (
                <div className="flex flex-col gap-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-slate-500 dark:text-slate-400">
                      {lostData.total} item{lostData.total !== 1 ? 's' : ''}
                    </span>
                    <Link to="/report/lost" className="btn-primary text-xs py-1.5 px-4">
                      + Report New
                    </Link>
                  </div>
                  {lostData.items.map((item) => (
                    <LostItemRow
                      key={item.id}
                      item={item}
                      onDelete={handleDelete}
                      onExtend={handleExtend}
                      deleting={deletingId === item.id}
                      extending={extendingId === item.id}
                    />
                  ))}
                </div>
              )
            )}
            {activeTab === 'found' && (
              foundLoading ? (
                <div className="flex justify-center py-16">
                  <div className="w-7 h-7 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
                </div>
              ) : !foundData?.items?.length ? (
                <EmptyTab
                  message="You haven't reported any found items yet. Help someone reunite with their belongings."
                  cta="Report Found Item"
                  ctaTo="/report/found"
                />
              ) : (
                <div className="flex flex-col gap-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-slate-500 dark:text-slate-400">
                      {foundData.total} item{foundData.total !== 1 ? 's' : ''}
                    </span>
                    <Link to="/report/found" className="btn-primary text-xs py-1.5 px-4">
                      + Report Found
                    </Link>
                  </div>
                  {foundData.items.map((item) => (
                    <FoundItemRow
                      key={item.id}
                      item={item}
                      onDelete={handleDeleteFound}
                      onExtend={handleExtendFound}
                      deleting={deletingFoundId === item.id}
                      extending={extendingFoundId === item.id}
                    />
                  ))}
                </div>
              )
            )}
            {activeTab === 'returned' && (
              returnsLoading ? (
                <div className="flex justify-center py-16">
                  <div className="w-7 h-7 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
                </div>
              ) : !returnsData?.items?.length ? (
                <EmptyTab
                  message="Items you've successfully returned or received back will appear here."
                />
              ) : (
                <div className="flex flex-col gap-3">
                  {returnsData.items.map((row) => (
                    <ReturnedRow key={row.return_id} row={row} />
                  ))}
                </div>
              )
            )}
            {activeTab === 'pending' && (
              matchesLoading ? (
                <div className="flex justify-center py-16">
                  <div className="w-7 h-7 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
                </div>
              ) : !matchData?.matches?.length ? (
                <EmptyTab
                  message="When our AI finds a potential match for your items, it will appear here. Post both lost and found items to trigger matching."
                />
              ) : (
                <div className="flex flex-col gap-4">
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    {matchData.total} potential match{matchData.total !== 1 ? 'es' : ''} — ranked by confidence
                  </p>
                  {matchData.matches.map((m) => (
                    <MatchRow key={m.id} match={m} />
                  ))}
                </div>
              )
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
