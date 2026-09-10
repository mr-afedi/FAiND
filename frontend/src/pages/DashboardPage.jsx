import { useState, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { userService } from '../services/userService'
import { getMyLostItems, deleteItem, extendItem,
         getMyFoundItems, deleteFoundItem, extendFoundItem } from '../services/itemService'
import { useAuth } from '../context/AuthContext'
import NavBar from '../components/NavBar'
import { getMyMatches } from '../services/matchService'
import { getMyClaims, getAwaitingConfirmation } from '../services/claimService'
import { listMyReturns } from '../services/returnService'
import { getMyTokens, redeemTokens } from '../services/tokenService'
import { invalidateAfterItemChange } from '../utils/queryCache'
import {
  CategoryIcon,
  getCategoryLabel,
  EmptyInboxIcon,
  MapPin,
  Bot,
  ClipboardList,
  Check,
} from '../components/icons'
import { ITEM_STATUS_PILL, formatItemStatus } from '../utils/itemStatusStyles'

const STATUS_CLASSES = ITEM_STATUS_PILL

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
            {formatItemStatus(item.status)}
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
            {formatItemStatus(item.status)}
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

// ── My Claims / Awaiting confirmation (V5) ────────────────────────────────────

const CLAIM_STATUS_PILL = {
  pending_review: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
  called_to_collect: 'bg-sky-100 text-sky-800 dark:bg-sky-900/30 dark:text-sky-300',
  rejected: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
}

function ClaimDashboardCard({ claim }) {
  return (
    <div className="flex flex-col sm:flex-row gap-3 p-4 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/50">
      <div className="flex-shrink-0">
        {claim.thumbnail_url ? (
          <img src={claim.thumbnail_url} alt="" className="w-16 h-16 rounded-xl object-cover" />
        ) : (
          <div className="w-16 h-16 rounded-xl bg-slate-100 dark:bg-slate-700 flex items-center justify-center">
            <CategoryIcon category={claim.category} className="w-7 h-7 text-slate-400" />
          </div>
        )}
      </div>
      <div className="flex-1 min-w-0 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-semibold text-slate-800 dark:text-slate-100">
            {getCategoryLabel(claim.category)}
          </span>
          <span className={`inline-flex px-2 py-0.5 rounded-lg text-xs font-medium ${CLAIM_STATUS_PILL[claim.viewer_state] || ''}`}>
            {claim.status_label}
          </span>
        </div>
        <p className="text-xs text-slate-600 dark:text-slate-400 line-clamp-2">{claim.description_preview}</p>
        <p className="text-xs text-slate-500">
          {claim.drop_point_name}
          {claim.operating_hours ? ` · ${claim.operating_hours}` : ''}
        </p>
        <Link to={`/claims/status/${claim.claim_id}`} className="btn-secondary text-xs py-1.5 px-3 inline-block mt-2">
          View Claim Status
        </Link>
      </div>
    </div>
  )
}

function AwaitingConfirmationCard({ item }) {
  return (
    <div className="flex flex-col sm:flex-row gap-3 p-4 rounded-xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50/50 dark:bg-emerald-900/10">
      <div className="flex-shrink-0">
        {item.thumbnail_url ? (
          <img src={item.thumbnail_url} alt="" className="w-16 h-16 rounded-xl object-cover" />
        ) : (
          <div className="w-16 h-16 rounded-xl bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
            <CategoryIcon category={item.category} className="w-7 h-7 text-emerald-600" />
          </div>
        )}
      </div>
      <div className="flex-1 min-w-0 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-semibold text-slate-800 dark:text-slate-100">
            {getCategoryLabel(item.category)}
          </span>
          <span className="inline-flex px-2 py-0.5 rounded-lg text-xs font-medium bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
            {item.status_label}
          </span>
        </div>
        <p className="text-xs text-slate-600 dark:text-slate-400 line-clamp-2">{item.description_preview}</p>
        <p className="text-xs text-slate-500">
          {item.drop_point_name}
          {item.operating_hours ? ` · ${item.operating_hours}` : ''}
        </p>
        {item.can_confirm && item.handover_id ? (
          <Link to={`/handover/${item.handover_id}`} className="btn-primary text-xs py-1.5 px-3 inline-block mt-2">
            Confirm I Collected This Item
          </Link>
        ) : (
          <p className="text-xs text-emerald-700 dark:text-emerald-300 mt-2">
            Please visit {item.drop_point_name} to collect your item.
          </p>
        )}
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
              Verified
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

      {isLostOwner && (status === 'active' || status === 'pending_review') && (
        <Link
          to={`/claims/found/${match.found_item.id}?path=a`}
          className="btn-primary text-sm py-2 w-full sm:w-auto text-center"
        >
          Verify Ownership
        </Link>
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
          {row.drop_point_name && (
            <> · Collected from {row.drop_point_name}</>
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

const TOKEN_REASON_LABELS = {
  found_item_posted: 'Posted a found item',
  drop_off_on_time: 'On-time drop-off',
  drop_off_late: 'Late drop-off',
  item_claimed: 'Item claimed by owner',
  redemption: 'Redemption',
  redemption_refund: 'Redemption refund',
}

function formatTokenReason(reason) {
  return TOKEN_REASON_LABELS[reason] ?? reason.replace(/_/g, ' ')
}

function formatTokenDate(iso) {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function RedeemTokensModal({ open, onClose, balance, onSuccess }) {
  const [amount, setAmount] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)

  useEffect(() => {
    if (!open) {
      setAmount('')
      setResult(null)
      setSubmitting(false)
    }
  }, [open])

  if (!open) return null

  async function handleSubmit(e) {
    e.preventDefault()
    const value = parseInt(amount, 10)
    if (!value || value < 1) {
      toast.error('Enter a valid token amount.')
      return
    }
    if (value > balance) {
      toast.error(`You only have ${balance} tokens.`)
      return
    }
    setSubmitting(true)
    try {
      const data = await redeemTokens(value)
      setResult(data)
      onSuccess?.(data)
      toast.success('Redemption code generated')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not generate code')
    } finally {
      setSubmitting(false)
    }
  }

  function copyCode() {
    if (!result?.code) return
    navigator.clipboard.writeText(result.code)
    toast.success('Code copied')
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="glass w-full max-w-md p-6 max-md:p-4" role="dialog" aria-modal="true">
        <div className="flex items-start justify-between gap-3 mb-4">
          <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">
            Redeem Tokens
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {!result ? (
          <>
            <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
              Enter how many tokens to redeem. They are deducted immediately and a one-time
              code is generated. Present the code to staff at a participating service.
              Unused codes expire after 30 days and tokens are refunded automatically.
            </p>
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-3">
              Available balance: <span className="tabular-nums">{balance}</span>
            </p>
            <form onSubmit={handleSubmit} className="space-y-4">
              <input
                type="number"
                min="1"
                max={balance}
                step="1"
                required
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="Token amount"
                className="input-field w-full"
              />
              <div className="flex gap-2 justify-end">
                <button type="button" onClick={onClose} className="btn-secondary text-sm">
                  Cancel
                </button>
                <button type="submit" disabled={submitting || balance < 1} className="btn-primary text-sm">
                  {submitting ? 'Generating…' : 'Generate Code'}
                </button>
              </div>
            </form>
          </>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Show this code to staff. It can only be used once and expires on{' '}
              {formatTokenDate(result.expires_at)}.
            </p>
            <div className="rounded-xl border-2 border-dashed border-brand-400/60 bg-brand-50/50 dark:bg-brand-950/30 p-4 text-center">
              <p className="text-xs uppercase tracking-wide text-slate-500 mb-1">Your code</p>
              <p className="text-2xl font-bold tracking-wider text-brand-700 dark:text-brand-300 font-mono">
                {result.code}
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-400 mt-2">
                {result.token_amount} token{result.token_amount !== 1 ? 's' : ''}
              </p>
            </div>
            <p className="text-xs text-slate-500">
              New balance: <span className="font-semibold tabular-nums">{result.balance_after}</span>
            </p>
            <div className="flex gap-2 justify-end">
              <button type="button" onClick={copyCode} className="btn-secondary text-sm">
                Copy Code
              </button>
              <button type="button" onClick={onClose} className="btn-primary text-sm">
                Done
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [searchParams] = useSearchParams()
  const [activeTab, setActiveTab] = useState('lost')
  const { logout } = useAuth()
  const [deletingId, setDeletingId]         = useState(null)
  const [extendingId, setExtendingId]       = useState(null)
  const [deletingFoundId, setDeletingFoundId]   = useState(null)
  const [extendingFoundId, setExtendingFoundId] = useState(null)
  const [redeemOpen, setRedeemOpen] = useState(false)
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

  const { data: matchData, isLoading: matchesLoading } = useQuery({
    queryKey: ['my-matches'],
    queryFn: getMyMatches,
    refetchInterval: activeTab === 'pending' ? 30_000 : false,
  })

  const { data: myClaimsData, isLoading: claimsLoading } = useQuery({
    queryKey: ['my-claims'],
    queryFn: getMyClaims,
    refetchInterval: activeTab === 'pending' ? 30_000 : false,
  })

  const { data: awaitingData, isLoading: awaitingLoading } = useQuery({
    queryKey: ['my-awaiting-confirmation'],
    queryFn: getAwaitingConfirmation,
    refetchInterval: activeTab === 'pending' ? 30_000 : false,
  })

  const { data: returnsData, isLoading: returnsLoading } = useQuery({
    queryKey: ['my-returns'],
    queryFn: listMyReturns,
  })

  const { data: tokensData, isLoading: tokensLoading } = useQuery({
    queryKey: ['my-tokens'],
    queryFn: getMyTokens,
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

      <div className="page-container py-8 max-md:py-5 max-w-5xl">
        {/* ── Profile header ── */}
        <div className="glass p-6 max-md:p-4 mb-6 max-md:mb-4 flex flex-col sm:flex-row items-start sm:items-center gap-4 max-md:gap-3">
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
            </div>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
              @{profile.username} · {profile.university_short_name} · Member since {profile.member_since}
            </p>
          </div>

          <Link to="/settings" className="btn-secondary text-sm flex-shrink-0 hidden md:inline-flex">
            Edit Profile
          </Link>
        </div>

        {/* Mobile account menu — profile, settings, logout */}
        <div className="md:hidden glass rounded-xl p-2 mb-4 flex flex-col divide-y divide-slate-200/60 dark:divide-slate-700/50">
          <Link
            to={`/profile/${profile.username}`}
            className="flex items-center gap-3 px-3 py-3 min-h-[44px] text-sm font-medium text-slate-700 dark:text-slate-300"
          >
            <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M17.982 18.725A7.488 7.488 0 0 0 12 15.75a7.488 7.488 0 0 0-5.982 2.975m11.963 0a9 9 0 1 0-11.963 0m11.963 0A8.966 8.966 0 0 1 12 21a8.966 8.966 0 0 1-5.982-2.275M15 9.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
            </svg>
            My Profile
          </Link>
          <Link
            to="/settings"
            className="flex items-center gap-3 px-3 py-3 min-h-[44px] text-sm font-medium text-slate-700 dark:text-slate-300"
          >
            <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
            </svg>
            Settings
          </Link>
          <button
            type="button"
            onClick={logout}
            className="flex items-center gap-3 w-full px-3 py-3 min-h-[44px] text-sm font-medium text-red-600 dark:text-red-400 text-left"
          >
            <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15m3 0 3-3m0 0-3-3m3 3H9" />
            </svg>
            Log out
          </button>
        </div>

        {/* ── Overview cards (Section 25.1) ── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 max-md:gap-2.5 mb-2">
          <StatCard
            label="Your Tokens"
            value={tokensLoading ? '…' : (tokensData?.balance ?? 0)}
            icon={
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
              </svg>
            }
            sub="Reward balance"
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
            label="Pending Matches"
            value={matchData?.total ?? 0}
            icon={<Bot className="w-6 h-6" aria-hidden />}
            sub="AI suggestions"
          />
        </div>

        {/* ── Token ledger (W11) ── */}
        <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
          <div />
          <button
            type="button"
            onClick={() => setRedeemOpen(true)}
            disabled={tokensLoading || (tokensData?.balance ?? 0) < 1}
            className="btn-primary text-sm"
          >
            Redeem Tokens
          </button>
        </div>

        {!tokensLoading && (tokensData?.recent?.length ?? 0) > 0 && (
          <div className="glass p-4 max-md:p-3 mb-4">
            <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
              Recent token activity
            </h2>
            <ul className="divide-y divide-slate-200/60 dark:divide-slate-700/50">
              {tokensData.recent.map((entry) => (
                <li
                  key={entry.id}
                  className="flex items-center justify-between gap-3 py-2.5 first:pt-0 last:pb-0"
                >
                  <div className="min-w-0">
                    <p className="text-sm text-slate-800 dark:text-slate-200 truncate">
                      {formatTokenReason(entry.reason)}
                    </p>
                    <p className="text-xs text-slate-400 dark:text-slate-500">
                      {formatTokenDate(entry.created_at)}
                    </p>
                  </div>
                  <span
                    className={`text-sm font-semibold tabular-nums shrink-0 ${
                      entry.delta >= 0
                        ? 'text-green-600 dark:text-green-400'
                        : 'text-red-600 dark:text-red-400'
                    }`}
                  >
                    {entry.delta >= 0 ? '+' : ''}{entry.delta}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="mb-4" />

        {/* ── Tabs (Section 25.2) ── */}
        <div className="glass overflow-hidden">
          {/* Tab bar */}
          <div className="flex gap-1 p-2 border-b border-slate-200/50 dark:border-slate-700/50 overflow-x-auto overscroll-x-contain scrollbar-thin">
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
          <div className="p-4 max-md:p-3">
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
              (matchesLoading || claimsLoading || awaitingLoading) ? (
                <div className="flex justify-center py-16">
                  <div className="w-7 h-7 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
                </div>
              ) : (
                <div className="flex flex-col gap-8">
                  {(awaitingData?.items?.length ?? 0) > 0 && (
                    <section className="space-y-3">
                      <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                        Awaiting Your Confirmation
                      </h3>
                      <div className="flex flex-col gap-4">
                        {awaitingData.items.map((item) => (
                          <AwaitingConfirmationCard key={item.claim_id} item={item} />
                        ))}
                      </div>
                    </section>
                  )}

                  {(myClaimsData?.claims?.length ?? 0) > 0 && (
                    <section className="space-y-3">
                      <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                        My Claims
                      </h3>
                      <div className="flex flex-col gap-4">
                        {myClaimsData.claims.map((claim) => (
                          <ClaimDashboardCard key={claim.claim_id} claim={claim} />
                        ))}
                      </div>
                    </section>
                  )}

                  {!matchData?.matches?.length
                    && !(myClaimsData?.claims?.length)
                    && !(awaitingData?.items?.length) ? (
                      <EmptyTab
                        message="When our AI finds a potential match for your items, or you submit a claim, it will appear here."
                      />
                    ) : matchData?.matches?.length ? (
                      <section className="space-y-3">
                        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                          Potential Matches
                        </h3>
                        <p className="text-sm text-slate-500 dark:text-slate-400">
                          {matchData.total} potential match{matchData.total !== 1 ? 'es' : ''} — ranked by confidence
                        </p>
                        <div className="flex flex-col gap-4">
                          {matchData.matches.map((m) => (
                            <MatchRow key={m.id} match={m} />
                          ))}
                        </div>
                      </section>
                    ) : null}
                </div>
              )
            )}
          </div>
        </div>
      </div>

      <RedeemTokensModal
        open={redeemOpen}
        onClose={() => setRedeemOpen(false)}
        balance={tokensData?.balance ?? 0}
        onSuccess={() => queryClient.invalidateQueries({ queryKey: ['my-tokens'] })}
      />
    </div>
  )
}
