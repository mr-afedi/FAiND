/**
 * Touch-friendly full-width item card for staff dashboards (mobile).
 */
import { MapPin, Clock, CheckCircle, AlertTriangle } from 'lucide-react'
import { CategoryIcon, getCategoryLabel } from '../icons'
import { LightboxImage } from '../ImageLightbox'
import {
  dropoffCountdownLabel,
  dropoffCountdownTone,
  countdownClassName,
  timeSincePosted,
} from './staffUtils'

function CountdownBanner({ item }) {
  if (!item) return null
  const tone = dropoffCountdownTone(item)
  const Icon = tone === 'green' ? CheckCircle : AlertTriangle
  return (
    <div className={`flex items-start gap-2 rounded-xl border px-3 py-2.5 text-sm font-medium
                     leading-snug ${countdownClassName(tone)}`}>
      <Icon className="w-5 h-5 shrink-0 mt-0.5" strokeWidth={1.75} aria-hidden />
      <span>{dropoffCountdownLabel(item)}</span>
    </div>
  )
}

export function StaffIncomingMobileCard({
  item,
  onOpenDetail,
  onPrimaryAction,
  primaryLabel,
  primaryLoading,
  onImageOpen,
  subtitle,
  alwaysVisible = false,
}) {
  return (
    <article
      className={`${alwaysVisible ? '' : 'md:hidden'} glass border border-slate-200 dark:border-slate-800/80 rounded-2xl p-4 space-y-3
                 active:bg-slate-100 dark:active:bg-slate-900/40 transition-colors`}
    >
      <button
        type="button"
        className="w-full text-left space-y-3"
        onClick={() => onOpenDetail?.(item)}
      >
        <div className="flex items-start gap-3">
          <div className="w-11 h-11 rounded-xl bg-slate-800 flex items-center justify-center shrink-0">
            <CategoryIcon category={item.category} className="w-6 h-6 text-brand-400" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-brand-600 dark:text-brand-300 uppercase tracking-wide">
              {getCategoryLabel(item.category)}
            </p>
            {subtitle && (
              <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>
            )}
            <p className="text-base font-semibold text-slate-900 dark:text-slate-100 mt-0.5 line-clamp-2 leading-snug">
              {item.public_description}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-400">
          <span className="inline-flex items-center gap-1.5 min-h-[44px]">
            <MapPin className="w-4 h-4 shrink-0" strokeWidth={1.75} aria-hidden />
            {item.location_label}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <Clock className="w-4 h-4 shrink-0" strokeWidth={1.75} aria-hidden />
            {timeSincePosted(item.created_at)}
          </span>
        </div>

        {item.image_urls?.length > 0 && (
          <div className="flex gap-2" onClick={(e) => e.stopPropagation()} role="presentation">
            {item.image_urls.slice(0, 3).map((url, i) => (
              <LightboxImage
                key={url}
                src={url}
                images={item.image_urls}
                index={i}
                onOpen={onImageOpen}
                className="w-16 h-16 rounded-lg overflow-hidden border border-slate-700"
              />
            ))}
          </div>
        )}

        <CountdownBanner item={item} />
      </button>

      {onPrimaryAction && (
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); onPrimaryAction(item) }}
          disabled={primaryLoading}
          className="btn-primary w-full min-h-[48px] text-base font-semibold"
        >
          {primaryLoading ? 'Confirming…' : primaryLabel}
        </button>
      )}
    </article>
  )
}

export function StaffAtDroppointMobileCard({ item, onOpenDetail, onImageOpen }) {
  return (
    <article className="md:hidden glass border border-emerald-900/40 rounded-2xl p-4 space-y-3">
      <button
        type="button"
        className="w-full text-left space-y-3"
        onClick={() => onOpenDetail?.(item)}
      >
        <div className="flex items-start gap-3">
          <div className="w-11 h-11 rounded-xl bg-emerald-950/60 flex items-center justify-center shrink-0">
            <CategoryIcon category={item.category} className="w-6 h-6 text-emerald-400" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-emerald-400 uppercase tracking-wide">
              Awaiting claim
            </p>
            <p className="text-base font-semibold text-slate-900 dark:text-slate-100 mt-0.5 line-clamp-2 leading-snug">
              {item.public_description}
            </p>
            <p className="text-sm text-slate-500 mt-1">{getCategoryLabel(item.category)}</p>
          </div>
        </div>

        <p className="text-sm text-slate-400 inline-flex items-center gap-1.5">
          <Clock className="w-4 h-4" strokeWidth={1.75} aria-hidden />
          Received {timeSincePosted(item.dropoff_confirmed_at || item.authority_received_at)}
          {item.dropoff_late && (
            <span className="text-amber-400 ml-1">(late drop-off)</span>
          )}
        </p>

        {item.image_urls?.length > 0 && (
          <div className="flex gap-2" onClick={(e) => e.stopPropagation()} role="presentation">
            {item.image_urls.slice(0, 3).map((url, i) => (
              <LightboxImage
                key={url}
                src={url}
                images={item.image_urls}
                index={i}
                onOpen={onImageOpen}
                className="w-16 h-16 rounded-lg overflow-hidden border border-slate-700"
              />
            ))}
          </div>
        )}
      </button>
    </article>
  )
}

export function StaffSupervisorItemMobileCard({ item, onOpenDetail }) {
  return (
    <article className="md:hidden glass border border-slate-800/80 rounded-2xl p-4 space-y-2">
      <button type="button" className="w-full text-left space-y-2" onClick={() => onOpenDetail?.(item)}>
        <p className="text-sm text-slate-500">{item.drop_point_name} · {item.status}</p>
        <p className="text-base font-semibold text-slate-900 dark:text-slate-100 line-clamp-2 leading-snug">
          {item.public_description}
        </p>
        <p className="text-sm text-slate-400 inline-flex items-center gap-1.5">
          <MapPin className="w-4 h-4" strokeWidth={1.75} aria-hidden />
          {item.location_label}
        </p>
      </button>
    </article>
  )
}
