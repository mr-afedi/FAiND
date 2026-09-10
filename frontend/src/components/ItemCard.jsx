/**
 * ItemCard — shared public browse card (Section 24.2).
 */
import { Link } from 'react-router-dom'
import { CategoryIcon, CategoryLabel, getCategoryMeta, MapPin } from './icons'
import { ITEM_STATUS_PILL, formatItemStatus } from '../utils/itemStatusStyles'
import ViewerClaimBanner from './ViewerClaimBanner'
import {
  isFinderForItem,
  shouldShowFinderTrack,
  getDropPointNameForItem,
} from '../utils/foundTracking'

const STATUS_PILL = ITEM_STATUS_PILL

function timeAgo(iso) {
  const diff = Math.floor((Date.now() - new Date(iso)) / 1000)
  if (diff < 60)       return 'just now'
  if (diff < 3600)     return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400)    return `${Math.floor(diff / 3600)}h ago`
  if (diff < 2592000)  return `${Math.floor(diff / 86400)}d ago`
  return new Date(iso).toLocaleDateString()
}

const VIEWER_BADGE_PILL =
  'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-300'

export default function ItemCard({ item, viewerBadge = null, viewerUserId = null }) {
  const cat = getCategoryMeta(item.category)
  const isFinder = isFinderForItem(item, viewerUserId)
  const showTrack = isFinder && shouldShowFinderTrack(item)
  const atDropPoint = isFinder && item.status === 'at_droppoint'
  const dropPointName = getDropPointNameForItem(item.id)

  return (
    <Link
      to={`/items/${item.id}`}
      className="group flex h-full max-md:flex-row flex-col rounded-2xl max-md:rounded-xl overflow-hidden border border-slate-200/70
                 dark:border-slate-700/50 bg-white dark:bg-slate-800/60
                 hover:shadow-lg hover:-translate-y-0.5 max-md:hover:translate-y-0 transition-all duration-200"
    >
      <div className="relative w-full flex-shrink-0 aspect-[4/3] max-md:w-[5.5rem] max-md:h-[5rem] max-md:aspect-auto
                      bg-slate-100 dark:bg-slate-700 overflow-hidden">
        {item.image_urls?.[0] ? (
          <img
            src={item.image_urls[0]}
            alt={cat.label}
            className="w-full h-full object-cover max-md:object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-slate-400">
            <CategoryIcon category={item.category} className="w-14 h-14 max-md:w-8 max-md:h-8" />
          </div>
        )}
        <span className={`absolute top-2 left-2 text-[10px] font-semibold px-2 py-0.5 rounded-full
                          ${item.item_type === 'lost'
                            ? 'bg-red-500/90 text-white'
                            : 'bg-brand-500/90 text-white'}`}>
          {item.item_type === 'lost' ? 'LOST' : 'FOUND'}
        </span>
        {showTrack && (
          <span className="absolute top-2 right-2 text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full
                           bg-sky-500/90 text-white">
            Track
          </span>
        )}
        {item.image_urls?.length > 1 && (
          <span className={`absolute ${showTrack ? 'bottom-2 right-2' : 'top-2 right-2'}
                           bg-black/50 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full`}>
            +{item.image_urls.length - 1}
          </span>
        )}
      </div>

      <div className="mt-auto max-md:mt-0 flex flex-col gap-2 max-md:gap-1 flex-1 min-w-0 p-3 max-md:py-2 max-md:pr-3 max-md:pl-2.5">
        <div className="flex flex-wrap items-center gap-1.5">
          <CategoryLabel
            category={item.category}
            className="text-xs font-semibold text-slate-700 dark:text-slate-200 min-w-0"
          />
          {viewerBadge ? (
            <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-lg ${VIEWER_BADGE_PILL}`}>
              {viewerBadge}
            </span>
          ) : item.status ? (
            <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-lg ${STATUS_PILL[item.status] ?? 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'}`}>
              {formatItemStatus(item.status)}
            </span>
          ) : null}
        </div>

        <p className="text-sm max-md:text-xs text-slate-700 dark:text-slate-300 line-clamp-2 max-md:line-clamp-1 leading-snug">
          {item.public_description}
        </p>

        {item.viewer_claim && item.item_type === 'found' && (
          <ViewerClaimBanner
            viewerClaim={item.viewer_claim}
            className="text-xs py-2 px-2.5"
          />
        )}

        {atDropPoint && (
          <p className="text-xs text-emerald-700 dark:text-emerald-300 leading-snug">
            Item is at {dropPointName || 'the drop point'} - awaiting collection by the owner.
          </p>
        )}

        <div className="flex items-center justify-between text-xs max-md:text-[10px] text-slate-400 dark:text-slate-500">
          <span className="truncate max-w-[60%] inline-flex items-center gap-1">
            <MapPin className="w-3 h-3 shrink-0" aria-hidden />
            {item.location_label}
          </span>
          <span className="flex-shrink-0">{timeAgo(item.created_at)}</span>
        </div>

        <div className="hidden md:flex items-center gap-1.5 pt-1 border-t border-slate-100 dark:border-slate-700/60">
          <span
            onClick={(e) => { e.preventDefault(); window.location.href = `/profile/${item.posted_by?.username}` }}
            className="text-xs text-slate-500 dark:text-slate-400 hover:text-brand-600
                       dark:hover:text-brand-400 hover:underline cursor-pointer truncate"
          >
            {item.posted_by?.display_name || item.posted_by?.username}
          </span>
        </div>
      </div>
    </Link>
  )
}
