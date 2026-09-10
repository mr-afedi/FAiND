/**
 * Supervisor Handover tab — read-only completed handovers across assigned drop points.
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { CheckCircle } from 'lucide-react'
import { getSupervisorHandoverQueue, getSupervisorHandover } from '../services/supervisorService'
import { useAuthorityLightbox } from '../context/AuthorityLightboxContext'
import { LightboxImage } from './ImageLightbox'
import { optimizeCloudinaryUrl } from '../utils/cloudinary'
import StaffMobileBottomSheet from './staff-mobile/StaffMobileBottomSheet'
import StaffDesktopDetailModal from './staff-mobile/StaffDesktopDetailModal'

function HandoverDetailBody({ detail, onImageOpen }) {
  if (!detail) return null
  const images = detail.found_item_image_urls || []
  return (
    <div className="space-y-4 text-sm">
      <div>
        <p className="text-xs text-slate-500 uppercase tracking-wide">Item</p>
        <p className="text-base font-semibold text-slate-900 dark:text-slate-100 mt-1">
          {detail.found_item_description}
        </p>
        {detail.drop_point_name && (
          <p className="text-xs text-slate-500 mt-1">{detail.drop_point_name}</p>
        )}
      </div>
      {images.length > 0 && (
        <div className="grid grid-cols-2 gap-2">
          {images.map((url, i) => (
            <LightboxImage
              key={url}
              src={optimizeCloudinaryUrl(url)}
              images={images.map((u) => optimizeCloudinaryUrl(u))}
              index={i}
              onOpen={onImageOpen}
              className="aspect-square rounded-xl object-cover w-full"
            />
          ))}
        </div>
      )}
      <div>
        <p className="text-xs text-slate-500">Claimant</p>
        <p className="text-slate-900 dark:text-slate-100">{detail.claimant_name}</p>
      </div>
      {detail.completed_at && (
        <div>
          <p className="text-xs text-slate-500">Completed</p>
          <p className="text-slate-700 dark:text-slate-300">
            {new Date(detail.completed_at).toLocaleString()}
          </p>
        </div>
      )}
      {detail.authority_override && detail.authority_override_note && (
        <div className="rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-500/30 p-3">
          <p className="text-xs font-semibold text-amber-800 dark:text-amber-200">Authority override</p>
          <p className="text-sm text-amber-900 dark:text-amber-100 mt-1">{detail.authority_override_note}</p>
        </div>
      )}
    </div>
  )
}

export default function SupervisorHandoverTab({ filterDp = '' }) {
  const openLightbox = useAuthorityLightbox()
  const [selectedId, setSelectedId] = useState(null)

  const { data, isLoading } = useQuery({
    queryKey: ['supervisor-handover', filterDp],
    queryFn: () => getSupervisorHandoverQueue(filterDp || undefined),
    refetchInterval: 30_000,
  })

  const { data: detail, isLoading: detailLoading } = useQuery({
    queryKey: ['supervisor-handover-detail', selectedId],
    queryFn: () => getSupervisorHandover(selectedId),
    enabled: Boolean(selectedId),
  })

  const items = (data?.items || []).filter((item) => item.queue_status === 'completed')

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!items.length) {
    return (
      <div className="glass p-8 text-center rounded-2xl">
        <p className="text-base text-slate-500 dark:text-slate-400">No completed handovers yet.</p>
      </div>
    )
  }

  return (
    <>
      <ul className="space-y-3">
        {items.map((item) => (
          <li key={item.handover_id || item.claim_id}>
            <button
              type="button"
              onClick={() => item.handover_id && setSelectedId(item.handover_id)}
              className="w-full glass rounded-2xl border border-slate-200 dark:border-slate-800/80 p-4 text-left
                         hover:border-brand-500/40 transition-colors min-h-[48px]"
            >
              <div className="flex items-start gap-3">
                <CheckCircle className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" aria-hidden />
                <div className="min-w-0 flex-1">
                  <p className="text-base font-medium text-slate-900 dark:text-slate-100 line-clamp-2">
                    {item.found_item_description}
                  </p>
                  <p className="text-sm text-slate-500 mt-1">
                    {item.claimant_name}
                    {item.drop_point_name && ` · ${item.drop_point_name}`}
                  </p>
                  {item.completed_at && (
                    <p className="text-xs text-slate-400 mt-1">
                      {new Date(item.completed_at).toLocaleString()}
                    </p>
                  )}
                </div>
              </div>
            </button>
          </li>
        ))}
      </ul>

      <StaffMobileBottomSheet
        open={Boolean(selectedId)}
        onClose={() => setSelectedId(null)}
        title="Handover detail"
      >
        {detailLoading && (
          <div className="flex justify-center py-8">
            <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
          </div>
        )}
        {!detailLoading && detail && (
          <HandoverDetailBody detail={detail} onImageOpen={openLightbox} />
        )}
      </StaffMobileBottomSheet>

      <StaffDesktopDetailModal
        open={Boolean(selectedId)}
        onClose={() => setSelectedId(null)}
        title="Handover detail"
      >
        {detailLoading && (
          <div className="flex justify-center py-12">
            <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
          </div>
        )}
        {!detailLoading && detail && (
          <HandoverDetailBody detail={detail} onImageOpen={openLightbox} />
        )}
      </StaffDesktopDetailModal>
    </>
  )
}
