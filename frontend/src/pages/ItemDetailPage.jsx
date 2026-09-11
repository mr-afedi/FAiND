/**
 * ItemDetailPage — /items/:id
 */
import { useState } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useAuth } from '../context/AuthContext'
import NavBar from '../components/NavBar'
import ReportModal from '../components/ReportModal'
import ItemUnavailablePage from './ItemUnavailablePage'
import FinderDropOffSection from '../components/FinderDropOffSection'
import FinderEditSection from '../components/FinderEditSection'
import {
  getItemDetail,
  deleteItem,
  deleteFoundItem,
  extendItem,
  extendFoundItem,
  getFoundItemByTrackingRef,
  getFoundItemFinderTrack,
} from '../services/itemService'
import { getMyMatches } from '../services/matchService'
import { invalidateAfterItemChange } from '../utils/queryCache'
import { pickPrimaryMatch } from '../utils/matchSelection'
import {
  CategoryIcon,
  CategoryLabel,
  getCategoryLabel,
  MapPin,
  AlertTriangle,
  X,
  ChevronLeft,
  ChevronRight,
  Flag,
  Clock,
  Trash2,
} from '../components/icons'
import { ITEM_STATUS_PILL, formatItemStatus, statusPillClass } from '../utils/itemStatusStyles'
import ViewerClaimBanner from '../components/ViewerClaimBanner'
import {
  isFinderForItem,
  shouldShowFinderTrack,
  getTrackingRefForItem,
  getDropPointNameForItem,
  saveFoundTrackingRef,
  getLatestTrackingRef,
} from '../utils/foundTracking'

const STATUS_PILL = ITEM_STATUS_PILL

function daysLeft(iso) {
  return Math.ceil((new Date(iso) - new Date()) / (1000 * 60 * 60 * 24))
}

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

export default function ItemDetailPage() {
  const { itemId } = useParams()
  const { user, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [lightboxIdx, setLightboxIdx] = useState(null)
  const [reportOpen, setReportOpen] = useState(false)

  const { data: item, isLoading, isError } = useQuery({
    queryKey: ['item', itemId],
    queryFn: () => getItemDetail(itemId),
  })

  const isOwner = item && user && item.posted_by?.id === user.id
  const isLost  = item?.item_type === 'lost'
  const isFinder = item && isFinderForItem(item, user?.id)
  const trackingRef = item ? getTrackingRefForItem(item.id) : ''
  const savedRef = trackingRef || getLatestTrackingRef()
  const showFinderPanel = Boolean(!isLost && (isFinder || isOwner || savedRef))

  const { data: finderTrackData, refetch: refetchFinderTrack } = useQuery({
    queryKey: ['finder-track', itemId, trackingRef, user?.id],
    queryFn: async () => {
      const refToTry = trackingRef || getLatestTrackingRef()
      if (refToTry) {
        try {
          const data = await getFoundItemByTrackingRef(refToTry)
          if (String(data.id) === String(itemId)) {
            saveFoundTrackingRef(refToTry, data.id, data.drop_point_name)
            return data
          }
        } catch {
          /* ref invalid or not for this item */
        }
      }
      if (isOwner && !isLost) {
        return getFoundItemFinderTrack(itemId)
      }
      return null
    },
    enabled: Boolean(showFinderPanel && itemId),
  })

  const isConfirmedFinder = showFinderPanel && finderTrackData && String(finderTrackData.id) === String(itemId)
  const showFinderTrack = isConfirmedFinder && (shouldShowFinderTrack(item) || item?.status === 'at_droppoint')

  const { data: matchData, isFetched: matchesFetched } = useQuery({
    queryKey: ['my-matches-for-item', itemId],
    queryFn: getMyMatches,
    enabled: Boolean(isAuthenticated),
  })
  const matchesReady = !isAuthenticated || matchesFetched

  const backTo    = isLost ? '/lost' : '/found'
  const backLabel = isLost ? 'Lost Items' : 'Found Items'
  const days      = item ? daysLeft(item.expiry_date) : 0

  const MASKED_PUBLIC_STATUSES = [
    'potential_match',
    'under_verification',
    'under_dispute',
    'under_claim_review',
  ]
  const ownerMatch = pickPrimaryMatch(
    matchData?.matches,
    (m) => m.user_role === 'lost_owner'
      && String(m.lost_item?.id) === String(itemId)
      && ['active', 'pending_review', 'verified'].includes(m.status),
  )
  const pathAMatch = !isLost && pickPrimaryMatch(
    matchData?.matches,
    (m) => m.user_role === 'lost_owner'
      && String(m.found_item?.id) === String(itemId)
      && ['active', 'pending_review'].includes(m.status),
  )
  const viewerClaim = item?.viewer_claim
  const needsInterestFlow = !isLost && ['found', 'overdue'].includes(item?.status)
  const canClaimPathC = matchesReady && !isLost && isAuthenticated && !isOwner && !pathAMatch && !viewerClaim
    && ['at_droppoint', 'under_claim_review'].includes(item?.status)
  const canRegisterInterest = matchesReady && !isLost && isAuthenticated && !isOwner && !pathAMatch && !viewerClaim
    && needsInterestFlow
  const ownerLostStatus = item && isOwner && isLost && item.status === 'potential_match' && !ownerMatch
    ? 'open'
    : item?.status
  const displayStatus = item && (
    isOwner
      ? ownerLostStatus
      : !isOwner && MASKED_PUBLIC_STATUSES.includes(item.status)
        ? (isLost ? 'open' : 'found')
        : item.status
  )
  const showStatusBadge = item && (
    isOwner
      ? Boolean(STATUS_PILL[displayStatus] || displayStatus)
      : !MASKED_PUBLIC_STATUSES.includes(item.status) && Boolean(STATUS_PILL[displayStatus] || displayStatus)
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

  const poster   = item.posted_by
  const initials = poster?.display_name
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

      <div className="page-container py-8 max-md:py-5 max-w-4xl overflow-x-hidden">
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

        {showFinderTrack && (
          <FinderDropOffSection
            itemId={itemId}
            trackingRef={trackingRef || null}
            trackData={finderTrackData}
            dropPointName={finderTrackData?.drop_point_name || getDropPointNameForItem(item.id)}
            onUpdated={(data) => {
              refetchFinderTrack()
              queryClient.invalidateQueries({ queryKey: ['item', itemId] })
              if (data) {
                queryClient.setQueryData(['finder-track', itemId, trackingRef, user?.id], data)
              }
            }}
          />
        )}

        {isConfirmedFinder && finderTrackData?.can_edit && (
          <FinderEditSection
            itemId={itemId}
            trackingRef={trackingRef || getLatestTrackingRef() || null}
            trackData={finderTrackData}
            onUpdated={async (data) => {
              if (data?.tracking_reference) {
                queryClient.setQueryData(['finder-track', itemId, trackingRef, user?.id], data)
              } else {
                await refetchFinderTrack()
              }
              queryClient.invalidateQueries({ queryKey: ['item', itemId] })
            }}
          />
        )}

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 max-md:gap-4">
          <div className="lg:col-span-2 flex flex-col gap-3 max-md:gap-2">
            {item.image_urls?.length > 0 ? (
              <>
                <div
                  className="w-full aspect-square max-md:aspect-[4/3] max-md:max-h-[220px] rounded-2xl max-md:rounded-xl overflow-hidden bg-slate-100
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

          <div className="lg:col-span-3 flex flex-col gap-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`text-xs font-bold px-2.5 py-1 rounded-full
                               ${isLost ? 'bg-red-500 text-white' : 'bg-brand-600 text-white'}`}>
                {isLost ? 'LOST' : 'FOUND'}
              </span>
              {showStatusBadge && (
                <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${statusPillClass(displayStatus)}`}>
                  {formatItemStatus(displayStatus)}
                </span>
              )}
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

            <div>
              <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100 mb-2">
                {isLost ? 'Lost Item' : 'Found Item'} Description
              </h1>
              <p className="text-slate-600 dark:text-slate-400 leading-relaxed text-sm">
                {item.public_description}
              </p>
            </div>

            <div className="glass p-3 rounded-xl flex flex-col gap-1.5 text-sm">
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

            <div className="flex items-center gap-3 p-3 glass rounded-xl">
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
              </div>
            </div>

            <div className="item-action-stack mt-auto">
              {viewerClaim && (
                <ViewerClaimBanner viewerClaim={viewerClaim} />
              )}

              {!isOwner && pathAMatch && isAuthenticated && !viewerClaim && (
                <Link
                  to={`/claims/found/${itemId}?path=a`}
                  className="btn-primary item-action-btn text-center"
                >
                  Verify Ownership
                </Link>
              )}

              {canClaimPathC && (
                <Link
                  to={`/claims/found/${itemId}?path=c`}
                  className="btn-primary item-action-btn text-center"
                >
                  This Might Be Mine
                </Link>
              )}

              {canRegisterInterest && (
                <Link
                  to={`/items/${itemId}/interest`}
                  className="btn-primary item-action-btn text-center"
                >
                  This Might Be Mine
                </Link>
              )}

              {!isOwner && !isAuthenticated && !isLost && !viewerClaim && (
                <button
                  type="button"
                  onClick={() => navigate('/login', { state: { from: `/items/${itemId}` } })}
                  className="btn-primary item-action-btn"
                >
                  This Might Be Mine
                </button>
              )}

              {!isOwner && (
                <button
                  type="button"
                  onClick={() => {
                    if (!isAuthenticated) navigate('/login', { state: { from: `/items/${itemId}` } })
                    else setReportOpen(true)
                  }}
                  className="item-report-link w-full"
                >
                  <Flag className="w-3.5 h-3.5 shrink-0" aria-hidden />
                  Flag / Report this post
                </button>
              )}

              {isOwner && (
                <div className="item-action-stack">
                  {item.status === 'returned' && (
                    <Link
                      to="/dashboard?tab=returned"
                      className="btn-secondary item-action-btn text-center"
                    >
                      View in Returned
                    </Link>
                  )}
                  {item.extensions_used < 2 && days > 0 && days <= 7 && (
                    <button
                      onClick={() => extendMutation.mutate(itemId)}
                      disabled={extendMutation.isPending}
                      className="btn-secondary item-action-btn"
                    >
                      {extendMutation.isPending ? 'Extending…' : (
                        <span className="inline-flex items-center justify-center gap-1.5">
                          <Clock className="w-3.5 h-3.5 shrink-0" aria-hidden />
                          Extend Post (+30 days)
                        </span>
                      )}
                    </button>
                  )}
                  <button
                    onClick={handleDelete}
                    disabled={deleteMutation.isPending}
                    className="item-btn-danger"
                  >
                    {deleteMutation.isPending ? 'Removing…' : (
                      <span className="inline-flex items-center justify-center gap-1.5">
                        <Trash2 className="w-3.5 h-3.5 shrink-0" aria-hidden />
                        Remove Post
                      </span>
                    )}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <ReportModal
        open={reportOpen}
        onClose={() => setReportOpen(false)}
        type="post"
        targetId={itemId}
        targetLabel={item?.public_description}
      />
    </div>
  )
}
