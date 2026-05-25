/**
 * ItemDetailPage — /items/:id  (Section 27.5)
 *
 * All users:
 *   - Back breadcrumb → browse page
 *   - Poster name/avatar → public profile
 *   - Category badge → browse page filtered by category
 *   - Images → fullscreen lightbox
 *
 * Logged-in (not owner):
 *   - "I Have This Item" (lost items) → placeholder (Feature I/J)
 *   - "This Might Be Mine" (found items) → placeholder (Feature K)
 *   - "Flag / Report Post" → placeholder (Feature P)
 *
 * Owner only:
 *   - Extend Post / Remove Post / Mark as Returned → stubs for future features
 */
import { useState } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useAuth } from '../context/AuthContext'
import NavBar from '../components/NavBar'
import ItemUnavailablePage from './ItemUnavailablePage'
import { getItemDetail, deleteItem, deleteFoundItem, extendItem, extendFoundItem } from '../services/itemService'
import { getMyMatches } from '../services/matchService'
import { invalidateAfterItemChange } from '../utils/queryCache'
import { matchVerificationInProgress, matchChatUnlocked } from '../utils/viewerItemBadges'
import {
  CategoryIcon,
  CategoryLabel,
  getCategoryLabel,
  MapPin,
  AlertTriangle,
  X,
  ChevronLeft,
  ChevronRight,
  Hand,
  ScanSearch,
  Flag,
  Clock,
  Trash2,
  Sparkles,
} from '../components/icons'

const STATUS_PILL = {
  open:               'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  found:              'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  potential_match:    'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400',
  under_verification: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  under_dispute:      'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  returned:           'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400',
}

const TIER_PILL = {
  'Community Champion': 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  'Reliable Member':    'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400',
  'Trusted Member':     'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  'New Member':         'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
}

function formatStatus(s) {
  return s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function daysLeft(iso) {
  return Math.ceil((new Date(iso) - new Date()) / (1000 * 60 * 60 * 24))
}

// ── Lightbox ──────────────────────────────────────────────────────────────────

function Lightbox({ images, startIdx, onClose }) {
  const [idx, setIdx] = useState(startIdx)

  return (
    <div
      className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center"
      onClick={onClose}
    >
      <button
        onClick={onClose}
        className="absolute top-4 right-4 text-white/70 hover:text-white text-2xl
                   w-10 h-10 flex items-center justify-center rounded-full
                   bg-white/10 hover:bg-white/20 transition-colors"
      >
        <X className="w-5 h-5" aria-hidden />
      </button>
      <img
        src={images[idx]}
        alt=""
        onClick={(e) => e.stopPropagation()}
        className="max-w-[90vw] max-h-[90vh] object-contain rounded-xl shadow-2xl"
      />
      {images.length > 1 && (
        <div className="absolute bottom-6 left-0 right-0 flex justify-center gap-3">
          {images.map((_, i) => (
            <button
              key={i}
              onClick={(e) => { e.stopPropagation(); setIdx(i) }}
              className={`w-2.5 h-2.5 rounded-full transition-all ${
                i === idx ? 'bg-white scale-125' : 'bg-white/40 hover:bg-white/70'
              }`}
            />
          ))}
        </div>
      )}
      {idx > 0 && (
        <button
          onClick={(e) => { e.stopPropagation(); setIdx((i) => i - 1) }}
          className="absolute left-4 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full
                     bg-white/10 hover:bg-white/20 text-white flex items-center justify-center"
        >
          <ChevronLeft className="w-5 h-5" aria-hidden />
        </button>
      )}
      {idx < images.length - 1 && (
        <button
          onClick={(e) => { e.stopPropagation(); setIdx((i) => i + 1) }}
          className="absolute right-4 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full
                     bg-white/10 hover:bg-white/20 text-white flex items-center justify-center"
        >
          <ChevronRight className="w-5 h-5" aria-hidden />
        </button>
      )}
    </div>
  )
}

// ── Item detail page ──────────────────────────────────────────────────────────

export default function ItemDetailPage() {
  const { itemId } = useParams()
  const { user, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [lightboxIdx, setLightboxIdx] = useState(null)

  const { data: item, isLoading, isError } = useQuery({
    queryKey: ['item', itemId],
    queryFn: () => getItemDetail(itemId),
  })

  const isOwner = item && user && item.posted_by?.id === user.id
  const isLost  = item?.item_type === 'lost'

  const { data: matchData } = useQuery({
    queryKey: ['my-matches-for-item', itemId],
    queryFn: getMyMatches,
    enabled: Boolean(isAuthenticated),
  })

  const ownerMatch = matchData?.matches?.find(
    (m) => m.user_role === 'lost_owner'
      && String(m.lost_item?.id) === String(itemId)
      && ['active', 'pending_review', 'verified'].includes(m.status),
  )

  const matchAsLostOwnerOnFound = matchData?.matches?.find(
    (m) => m.user_role === 'lost_owner'
      && String(m.found_item?.id) === String(itemId)
      && ['active', 'pending_review', 'verified'].includes(m.status),
  )

  const matchAsFoundOwnerOnFound = matchData?.matches?.find(
    (m) => m.user_role === 'found_owner'
      && String(m.found_item?.id) === String(itemId)
      && ['active', 'pending_review', 'verified'].includes(m.status),
  )

  const matchAsFoundOwnerOnLost = matchData?.matches?.find(
    (m) => m.user_role === 'found_owner'
      && String(m.lost_item?.id) === String(itemId)
      && ['active', 'pending_review', 'verified'].includes(m.status),
  )

  const isFinderUser = Boolean(
    matchData?.matches?.some((m) => m.user_role === 'found_owner'),
  )

  const foundOwnerMatchedOnLost = Boolean(matchAsFoundOwnerOnLost)
  const foundOwnerViewingMatchedLost = Boolean(
    matchAsFoundOwnerOnLost && matchVerificationInProgress(matchAsFoundOwnerOnLost),
  )
  const foundOwnerChatOpenOnLost = Boolean(
    matchAsFoundOwnerOnLost && matchChatUnlocked(matchAsFoundOwnerOnLost),
  )

  const backTo    = isLost ? '/lost' : '/found'
  const backLabel = isLost ? 'Lost Items' : 'Found Items'
  const days      = item ? daysLeft(item.expiry_date) : 0

  // Path B/C: only block claims on terminal statuses (not during verification)
  const NON_CLAIMABLE_STATUSES = ['returned', 'expired', 'archived', 'closed']
  const isClaimable = item && !NON_CLAIMABLE_STATUSES.includes(item.status)

  const lostOwnerViewingMatchedFound = Boolean(matchAsLostOwnerOnFound)
  const displayStatus = item && (
    !isOwner && item.status === 'under_verification'
      ? (isLost ? 'open' : 'found')
      : item.status
  )
  const showStatusBadge = item && (
    isOwner
      ? STATUS_PILL[item.status]
      : item.status !== 'under_verification' && STATUS_PILL[displayStatus]
  )

  const deleteMutation = useMutation({
    mutationFn: (id) => (isLost ? deleteItem(id) : deleteFoundItem(id)),
    onSuccess: (_data, id) => {
      invalidateAfterItemChange(queryClient, id)
      toast.success('Item removed')
      navigate(backTo)
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to remove item'),
  })

  const extendMutation = useMutation({
    mutationFn: (id) => (isLost ? extendItem(id) : extendFoundItem(id)),
    onSuccess: (_data, id) => {
      invalidateAfterItemChange(queryClient, id)
      toast.success('Expiry extended by 30 days')
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to extend'),
  })

  function handleDelete() {
    if (!confirm('Remove this item? It will be archived and hidden from the feed.')) return
    deleteMutation.mutate(itemId)
  }

  function handleClaimAction() {
    if (!isAuthenticated) {
      navigate('/login', { state: { from: `/items/${itemId}` } })
      return
    }
    toast('Claim flows are coming in a future update.', {
      icon: <Sparkles className="w-5 h-5 text-brand-500" aria-hidden />,
    })
  }

  if (isLoading) {
    return (
      <>
        <NavBar />
        <div className="page-container py-20 flex justify-center">
          <div className="w-9 h-9 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
        </div>
      </>
    )
  }

  if (isError || !item) {
    return <ItemUnavailablePage />
  }

  const poster     = item.posted_by
  const tierLabel  = poster?.trust_tier ?? 'New Member'
  const initials   = poster?.display_name
    ? poster.display_name.split(' ').map((n) => n[0]).slice(0, 2).join('').toUpperCase()
    : poster?.username?.[0]?.toUpperCase() ?? '?'

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 transition-colors duration-200">
      <NavBar />

      {lightboxIdx !== null && (
        <Lightbox
          images={item.image_urls}
          startIdx={lightboxIdx}
          onClose={() => setLightboxIdx(null)}
        />
      )}

      <div className="page-container py-8 max-w-4xl">
        {/* ── Breadcrumb ── */}
        <div className="flex items-center gap-2 mb-6 text-sm text-slate-500 dark:text-slate-400">
          <Link to={backTo} className="inline-flex items-center gap-1 hover:text-brand-600 dark:hover:text-brand-400 transition-colors">
            <ChevronLeft className="w-4 h-4 shrink-0" aria-hidden />
            {backLabel}
          </Link>
          <span>/</span>
          <span className="text-slate-700 dark:text-slate-300 truncate max-w-xs inline-flex items-center gap-1">
            <CategoryIcon category={item.category} className="w-3.5 h-3.5" />
            {getCategoryLabel(item.category)}
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* ── Left: images ── */}
          <div className="lg:col-span-2 flex flex-col gap-3">
            {item.image_urls?.length > 0 ? (
              <>
                <div
                  className="w-full aspect-square rounded-2xl overflow-hidden bg-slate-100
                             dark:bg-slate-800 cursor-zoom-in"
                  onClick={() => setLightboxIdx(0)}
                >
                  <img
                    src={item.image_urls[0]}
                    alt="Item photo"
                    className="w-full h-full object-contain"
                  />
                </div>
                {item.image_urls.length > 1 && (
                  <div className="grid grid-cols-2 gap-2">
                    {item.image_urls.slice(1).map((url, i) => (
                      <div
                        key={i}
                        className="aspect-square rounded-xl overflow-hidden bg-slate-100
                                   dark:bg-slate-800 cursor-zoom-in"
                        onClick={() => setLightboxIdx(i + 1)}
                      >
                        <img src={url} alt=""
                             className="w-full h-full object-contain" />
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <div className="w-full aspect-square rounded-2xl bg-slate-100 dark:bg-slate-800
                              flex items-center justify-center text-slate-400">
                <CategoryIcon category={item.category} className="w-14 h-14" />
              </div>
            )}
          </div>

          {/* ── Right: details + actions ── */}
          <div className="lg:col-span-3 flex flex-col gap-4">
            {/* Type + Status badges */}
            <div className="flex flex-wrap items-center gap-2">
              <span className={`text-xs font-bold px-2.5 py-1 rounded-full
                               ${isLost ? 'bg-red-500 text-white' : 'bg-brand-600 text-white'}`}>
                {isLost ? 'LOST' : 'FOUND'}
              </span>
              {showStatusBadge && (
                <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${STATUS_PILL[displayStatus]}`}>
                  {formatStatus(displayStatus)}
                </span>
              )}
              {/* Category — links back to browse filtered by category (Section 27.5) */}
              <Link
                to={`${backTo}?category=${item.category}`}
                className="text-xs font-medium px-2.5 py-1 rounded-full
                           bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300
                           hover:bg-brand-50 dark:hover:bg-brand-900/20 hover:text-brand-600
                           transition-colors"
              >
                <CategoryLabel category={item.category} className="text-xs font-medium" />
              </Link>
            </div>

            {/* Description */}
            <div>
              <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100 mb-2">
                {isLost ? 'Lost Item' : 'Found Item'} Description
              </h1>
              <p className="text-slate-600 dark:text-slate-400 leading-relaxed text-sm">
                {item.public_description}
              </p>
            </div>

            {/* Meta info */}
            <div className="glass p-4 rounded-2xl flex flex-col gap-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">Location</span>
                <span className="font-medium text-slate-700 dark:text-slate-300 inline-flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5 shrink-0" aria-hidden />
                  {item.location_label}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">
                  {isLost ? 'Date Lost' : 'Date Found'}
                </span>
                <span className="font-medium text-slate-700 dark:text-slate-300">
                  {new Date(item.date_occurred).toLocaleDateString('en-GB', {
                    day: 'numeric', month: 'short', year: 'numeric',
                  })}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">Posted</span>
                <span className="font-medium text-slate-700 dark:text-slate-300">
                  {new Date(item.created_at).toLocaleDateString('en-GB', {
                    day: 'numeric', month: 'short', year: 'numeric',
                  })}
                </span>
              </div>
              {days > 0 && (
                <div className="flex justify-between">
                  <span className="text-slate-500 dark:text-slate-400">Expires</span>
                  <span className={`font-medium ${days <= 3
                    ? 'text-orange-600 dark:text-orange-400'
                    : 'text-slate-700 dark:text-slate-300'}`}>
                    {days <= 3 ? (
                      <span className="inline-flex items-center gap-1">
                        <AlertTriangle className="w-3.5 h-3.5 shrink-0" aria-hidden />
                        In {days}d
                      </span>
                    ) : `In ${days}d`}
                  </span>
                </div>
              )}
            </div>

            {/* Poster info */}
            <div className="flex items-center gap-3 p-4 glass rounded-2xl">
              <Link to={`/profile/${poster?.username}`}
                    className="flex-shrink-0 w-10 h-10 rounded-full bg-brand-600
                               flex items-center justify-center text-white text-sm font-bold
                               hover:ring-2 hover:ring-brand-400 transition-all">
                {initials}
              </Link>
              <div className="flex-1 min-w-0">
                <Link to={`/profile/${poster?.username}`}
                      className="text-sm font-semibold text-slate-800 dark:text-slate-100
                                 hover:text-brand-600 dark:hover:text-brand-400 transition-colors truncate block">
                  {poster?.display_name || poster?.username}
                </Link>
                <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full
                                  ${TIER_PILL[tierLabel] ?? TIER_PILL['New Member']}`}>
                  {tierLabel}
                </span>
              </div>
            </div>

            {/* ── Action buttons ── */}
            <div className="flex flex-col gap-2 mt-auto">
              {/* Non-owner, logged-in or guest */}
              {!isOwner && (
                <>
                  {lostOwnerViewingMatchedFound && matchAsLostOwnerOnFound?.status === 'pending_review' && (
                    <p className="text-sm text-center text-amber-700 dark:text-amber-300 py-3 px-4
                                  rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200/80
                                  dark:border-amber-800/50">
                      Your ownership verification for this item is currently under admin review.
                    </p>
                  )}
                  {lostOwnerViewingMatchedFound && matchAsLostOwnerOnFound?.status === 'active' && (
                    <Link
                      to={`/verify-ownership/${matchAsLostOwnerOnFound.id}`}
                      className="btn-primary w-full py-3 text-sm font-semibold text-center"
                    >
                      Verify Ownership
                    </Link>
                  )}
                  {lostOwnerViewingMatchedFound && matchAsLostOwnerOnFound?.status === 'verified'
                    && matchAsLostOwnerOnFound.conversation_id && (
                    <Link
                      to={`/messages/${matchAsLostOwnerOnFound.conversation_id}`}
                      className="btn-primary w-full py-3 text-sm font-semibold text-center"
                    >
                      Open Chat
                    </Link>
                  )}
                  {foundOwnerViewingMatchedLost && (
                    <p className="text-sm text-center text-violet-700 dark:text-violet-300 py-3 px-4
                                  rounded-xl bg-violet-50 dark:bg-violet-900/20 border border-violet-200/80
                                  dark:border-violet-800/50">
                      An ownership claim is in progress for your matched item
                    </p>
                  )}
                  {foundOwnerChatOpenOnLost && (
                    <p className="text-sm text-center text-green-700 dark:text-green-300 py-3 px-4
                                  rounded-xl bg-green-50 dark:bg-green-900/20 border border-green-200/80
                                  dark:border-green-800/50">
                      You are matched with this item and chat is open
                    </p>
                  )}
                  {foundOwnerMatchedOnLost && matchAsFoundOwnerOnLost?.status === 'active' && (
                    <p className="text-sm text-center text-slate-600 dark:text-slate-400 py-3 px-4
                                  rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/80
                                  dark:border-slate-700/50">
                      You are already matched with this item. Waiting for the owner to verify ownership.
                    </p>
                  )}
                  {!lostOwnerViewingMatchedFound && !foundOwnerMatchedOnLost && isClaimable && isLost && (
                    <button
                      onClick={handleClaimAction}
                      className="btn-primary w-full py-3 text-sm font-semibold inline-flex items-center justify-center gap-2"
                    >
                      <Hand className="w-4 h-4 shrink-0" aria-hidden />
                      I Have This Item
                    </button>
                  )}
                  {!lostOwnerViewingMatchedFound && !foundOwnerMatchedOnLost && isClaimable && !isLost && !isFinderUser && (
                    <button
                      onClick={handleClaimAction}
                      className="btn-primary w-full py-3 text-sm font-semibold inline-flex items-center justify-center gap-2"
                    >
                      <ScanSearch className="w-4 h-4 shrink-0" aria-hidden />
                      This Might Be Mine
                    </button>
                  )}
                  {!lostOwnerViewingMatchedFound && !foundOwnerMatchedOnLost && !isClaimable && item && (
                    <p className="text-xs text-center text-slate-400 dark:text-slate-500 py-2">
                      This item is currently {formatStatus(displayStatus)} and cannot accept new claims.
                    </p>
                  )}
                  {!foundOwnerViewingMatchedLost && (
                    <button
                      onClick={() => {
                        if (!isAuthenticated) navigate('/login', { state: { from: `/items/${itemId}` } })
                        else toast('Report flow coming in a future update.', {
                          icon: <Flag className="w-5 h-5 text-red-500" aria-hidden />,
                        })
                      }}
                      className="text-xs text-slate-400 hover:text-red-500 dark:hover:text-red-400
                                 transition-colors text-center py-1 inline-flex items-center justify-center gap-1 w-full"
                    >
                      <Flag className="w-3.5 h-3.5 shrink-0" aria-hidden />
                      Flag / Report this post
                    </button>
                  )}
                </>
              )}

              {/* Owner actions */}
              {isOwner && (
                <div className="flex flex-col gap-2">
                  {ownerMatch?.status === 'active' && (
                    <Link
                      to={`/verify-ownership/${ownerMatch.id}`}
                      className="btn-primary w-full py-3 text-sm font-semibold text-center"
                    >
                      Verify Ownership
                    </Link>
                  )}
                  {isLost && ownerMatch?.status === 'pending_review' && (
                    <p className="text-sm text-center text-amber-700 dark:text-amber-300 py-3 px-4
                                  rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200/80
                                  dark:border-amber-800/50">
                      Your claim on a matched found item is currently under admin review.
                    </p>
                  )}
                  {!isLost && matchAsFoundOwnerOnFound?.status === 'pending_review' && (
                    <p className="text-sm text-center text-amber-700 dark:text-amber-300 py-3 px-4
                                  rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200/80
                                  dark:border-amber-800/50">
                      Admin is currently reviewing an ownership claim for this item.
                    </p>
                  )}
                  {ownerMatch?.status === 'verified' && ownerMatch.conversation_id && (
                    <Link
                      to={`/messages/${ownerMatch.conversation_id}`}
                      className="btn-primary w-full py-3 text-sm font-semibold text-center"
                    >
                      Open Chat
                    </Link>
                  )}
                  {item.extensions_used < 2 && days > 0 && days <= 7 && (
                    <button
                      onClick={() => extendMutation.mutate(itemId)}
                      disabled={extendMutation.isPending}
                      className="btn-secondary w-full py-2.5 text-sm"
                    >
                      {extendMutation.isPending ? 'Extending…' : (
                        <span className="inline-flex items-center justify-center gap-2">
                          <Clock className="w-4 h-4 shrink-0" aria-hidden />
                          Extend Post (+30 days)
                        </span>
                      )}
                    </button>
                  )}
                  <button
                    onClick={handleDelete}
                    disabled={deleteMutation.isPending}
                    className="w-full py-2.5 text-sm rounded-xl border border-red-200 text-red-600
                               hover:bg-red-50 dark:border-red-800 dark:text-red-400
                               dark:hover:bg-red-900/20 transition-colors disabled:opacity-50"
                  >
                    {deleteMutation.isPending ? 'Removing…' : (
                      <span className="inline-flex items-center justify-center gap-2">
                        <Trash2 className="w-4 h-4 shrink-0" aria-hidden />
                        Remove Post
                      </span>
                    )}
                  </button>
                  <p className="text-xs text-center text-slate-400 dark:text-slate-500">
                    Mark as Returned and Claim flows coming in future updates.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
