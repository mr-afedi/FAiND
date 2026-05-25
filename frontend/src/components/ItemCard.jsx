/**
 * ItemCard — shared public browse card (Section 24.2).
 * Shows: photo/icon, category badge, description, location, timestamp,
 *        poster tier badge + display name → public profile.
 */
import { Link } from 'react-router-dom'
import { CategoryIcon, CategoryLabel, getCategoryMeta, MapPin } from './icons'

const STATUS_PILL = {
  open:               'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  found:              'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  potential_match:    'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400',
  under_verification: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  under_dispute:      'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
}

const TIER_PILL = {
  'Community Champion': 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  'Reliable Member':    'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400',
  'Trusted Member':     'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  'New Member':         'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
}

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

export default function ItemCard({ item, viewerBadge = null }) {
  const cat  = getCategoryMeta(item.category)
  const tier = item.posted_by?.trust_tier ?? 'New Member'

  return (
    <Link
      to={`/items/${item.id}`}
      className="group flex h-full flex-col rounded-2xl overflow-hidden border border-slate-200/70
                 dark:border-slate-700/50 bg-white dark:bg-slate-800/60
                 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200"
    >
      {/* Image — flex-shrink-0 so grid row stretch never compresses the photo area */}
      <div className="relative w-full flex-shrink-0 aspect-[4/3] bg-slate-100 dark:bg-slate-700 overflow-hidden">
        {item.image_urls?.[0] ? (
          <img
            src={item.image_urls[0]}
            alt={cat.label}
            className="w-full h-full object-contain"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-slate-400">
            <CategoryIcon category={item.category} className="w-14 h-14" />
          </div>
        )}
        {/* Item type badge top-left */}
        <span className={`absolute top-2 left-2 text-[10px] font-semibold px-2 py-0.5 rounded-full
                          ${item.item_type === 'lost'
                            ? 'bg-red-500/90 text-white'
                            : 'bg-brand-500/90 text-white'}`}>
          {item.item_type === 'lost' ? 'LOST' : 'FOUND'}
        </span>
        {/* Multi-image count */}
        {item.image_urls?.length > 1 && (
          <span className="absolute top-2 right-2 bg-black/50 text-white text-[10px]
                           font-bold px-1.5 py-0.5 rounded-full">
            +{item.image_urls.length - 1}
          </span>
        )}
      </div>

      {/* Body — natural height; mt-auto absorbs extra space when grid rows are equalized */}
      <div className="mt-auto flex flex-col gap-2 p-3">
        {/* Category + status */}
        <div className="flex flex-wrap items-center gap-1.5">
          <CategoryLabel
            category={item.category}
            className="text-xs font-semibold text-slate-700 dark:text-slate-200 min-w-0"
          />
          {viewerBadge ? (
            <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-lg ${VIEWER_BADGE_PILL}`}>
              {viewerBadge}
            </span>
          ) : STATUS_PILL[item.status] ? (
            <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-lg ${STATUS_PILL[item.status]}`}>
              {item.status.replace(/_/g, ' ')}
            </span>
          ) : null}
        </div>

        {/* Description preview */}
        <p className="text-sm text-slate-700 dark:text-slate-300 line-clamp-2 leading-snug">
          {item.public_description}
        </p>

        {/* Location + time */}
        <div className="flex items-center justify-between text-xs text-slate-400 dark:text-slate-500">
          <span className="truncate max-w-[60%] inline-flex items-center gap-1">
            <MapPin className="w-3 h-3 shrink-0" aria-hidden />
            {item.location_label}
          </span>
          <span className="flex-shrink-0">{timeAgo(item.created_at)}</span>
        </div>

        {/* Poster */}
        <div className="flex items-center gap-1.5 pt-1 border-t border-slate-100 dark:border-slate-700/60">
          <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${TIER_PILL[tier] ?? TIER_PILL['New Member']}`}>
            {tier}
          </span>
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
