/**
 * Track My Found Item — anonymous finder can view/edit via tracking reference (Section 7.3–7.4).
 */
import { useState, useEffect, useMemo } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import NavBar from '../components/NavBar'
import CategoryPicker from '../components/CategoryPicker'
import ImageUploadSlot from '../components/ImageUploadSlot'
import SubmitButton from '../components/SubmitButton'
import { useSubmitLock } from '../hooks/useSubmitLock'
import {
  getFoundItemByTrackingRef,
  updateFoundItemByTrackingRef,
  confirmFoundDropOffByTrackingRef,
  uploadImageToCloudinary,
} from '../services/itemService'
import { getLatestTrackingRef, saveFoundTrackingRef } from '../utils/foundTracking'
import { saveEscrowToken } from '../utils/tokenEscrow'
import { invalidateAfterDropOff } from '../utils/queryCache'
import FinderTokenPrompt from '../components/FinderTokenPrompt'
import { getCategoryLabel, MapPin } from '../components/icons'

function DropOffPanel({ item, activeRef, onUpdated, onTokenEscrow }) {
  const queryClient = useQueryClient()
  const dropOff = item.drop_off || {}
  const qrImgUrl = dropOff.qr_image_data_url
    || (dropOff.qr_payload
      ? `https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=${encodeURIComponent(dropOff.qr_payload)}`
      : null)

  const { mutate: confirmDropOff, isPending } = useMutation({
    mutationFn: () => confirmFoundDropOffByTrackingRef(activeRef),
    onSuccess: (data) => {
      if (data.token_escrow?.escrow_token) {
        saveEscrowToken(data.token_escrow.escrow_token)
      }
      invalidateAfterDropOff(queryClient, { itemId: data.item?.id || item.id, trackingRef: activeRef })
      onUpdated(data.item)
      if (data.token_escrow) onTokenEscrow?.(data.token_escrow)
      toast.success(data.message)
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Could not confirm drop-off'),
  })

  if (dropOff.dropoff_phase === 'at_droppoint') {
    return (
      <div className="glass p-5 border border-emerald-200/70 dark:border-emerald-800/50 space-y-3">
        <p className="text-sm font-semibold text-emerald-700 dark:text-emerald-300">
          Drop-off confirmed
        </p>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          This item has been received at the drop point.
          {dropOff.dropoff_late && ' (Late drop-off — reduced token reward may apply.)'}
        </p>
        {item.token_escrow?.expiring_soon && item.token_escrow.pending_total > 0 && (
          <p className="text-sm text-amber-700 dark:text-amber-300 border border-amber-300/50 rounded-lg p-3">
            Your pending tokens ({item.token_escrow.pending_total}) expire within 24 hours.
            Create an account or sign in to claim them before they are lost.
          </p>
        )}
      </div>
    )
  }

  if (dropOff.dropoff_phase === 'unconfirmed') {
    return (
      <div className="glass p-5 border border-red-200/70 dark:border-red-900/50">
        <p className="text-sm font-semibold text-red-700 dark:text-red-300">
          No longer accepting drop-off
        </p>
        <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
          The 72-hour window has passed without confirmation. This report is closed for drop-off.
        </p>
      </div>
    )
  }

  return (
    <div className="glass p-5 space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">
          Drop-off deadline
        </h2>
        {dropOff.dropoff_phase === 'overdue' && (
          <span className="text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full
                           bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">
            Overdue
          </span>
        )}
        {dropOff.dropoff_phase === 'finder_confirmed' && (
          <span className="text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full
                           bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-200">
            Awaiting receipt
          </span>
        )}
      </div>

      {dropOff.hours_remaining > 0 ? (
        <p className="text-sm text-slate-600 dark:text-slate-400">
          <strong className="text-slate-800 dark:text-slate-100">{dropOff.hours_remaining}</strong>
          {' '}hour{dropOff.hours_remaining !== 1 ? 's' : ''} remaining to drop off on time.
        </p>
      ) : dropOff.hours_until_unconfirmed > 0 ? (
        <p className="text-sm text-amber-700 dark:text-amber-300">
          Past the 48-hour on-time window — you can still drop off for{' '}
          <strong>{dropOff.hours_until_unconfirmed}</strong> more hour
          {dropOff.hours_until_unconfirmed !== 1 ? 's' : ''}.
        </p>
      ) : null}

      {dropOff.show_dropoff_reminder && (
        <p className="text-xs text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/20
                        border border-amber-200 dark:border-amber-800 rounded-lg px-3 py-2">
          Reminder: please drop this item off at the drop point soon.
        </p>
      )}

      {qrImgUrl && (
        <div className="text-center">
          <p className="text-xs text-slate-500 mb-2">Show this QR code at the drop point</p>
          <img
            src={qrImgUrl}
            alt="Drop-off QR code"
            className="mx-auto rounded-lg border border-slate-200 dark:border-slate-700 min-w-[200px] min-h-[200px] w-[240px] h-[240px] object-contain"
            width={240}
            height={240}
          />
          {dropOff.qr_payload && (
            <p className="text-[10px] font-mono text-slate-400 mt-2 break-all px-2">
              {dropOff.qr_payload}
            </p>
          )}
          {dropOff.qr_consumed && (
            <p className="text-xs text-slate-400 mt-2">QR code already used</p>
          )}
        </div>
      )}

      {dropOff.can_confirm_drop_off && (
        <button
          type="button"
          onClick={() => confirmDropOff()}
          disabled={isPending}
          className="btn-primary w-full sm:w-auto text-sm"
        >
          {isPending ? 'Confirming…' : 'I Dropped This Off'}
        </button>
      )}

      {dropOff.finder_dropped_off_at && !dropOff.authority_received_at && (
        <p className="text-xs text-slate-500">
          You marked this as dropped off. Waiting for the drop point to confirm receipt.
        </p>
      )}
    </div>
  )
}

export default function TrackFoundItemPage() {
  const queryClient = useQueryClient()
  const [searchParams] = useSearchParams()
  const refFromUrl = (searchParams.get('ref') || '').trim().toUpperCase()
  const [inputRef, setInputRef] = useState(refFromUrl || getLatestTrackingRef())
  const [activeRef, setActiveRef] = useState(refFromUrl || '')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState('')
  const [images, setImages] = useState([null, null])
  const [uploadingIdx, setUploadingIdx] = useState(null)
  const [tokenEscrow, setTokenEscrow] = useState(null)
  const [promptDismissed, setPromptDismissed] = useState(false)
  const { isSubmitting, tryAcquire, release } = useSubmitLock()

  useEffect(() => {
    if (refFromUrl) {
      saveFoundTrackingRef(refFromUrl)
      setInputRef(refFromUrl)
      setActiveRef(refFromUrl)
      return
    }
    const saved = getLatestTrackingRef()
    if (saved) {
      setInputRef(saved)
      setActiveRef(saved)
    }
  }, [refFromUrl])

  const { data: item, isLoading, isError, refetch } = useQuery({
    queryKey: ['found-track', activeRef],
    queryFn: () => getFoundItemByTrackingRef(activeRef),
    enabled: Boolean(activeRef),
    retry: false,
  })

  useEffect(() => {
    if (!item) return
    setDescription(item.public_description || '')
    setCategory(item.category || '')
    const slots = [null, null]
    ;(item.image_urls || []).slice(0, 2).forEach((url, i) => {
      slots[i] = { url }
    })
    setImages(slots)
  }, [item?.id])

  useEffect(() => {
    if (!item?.token_escrow) return
    if (item.token_escrow.show_registration_prompt) {
      setTokenEscrow(item.token_escrow)
      if (item.token_escrow.escrow_token) {
        saveEscrowToken(item.token_escrow.escrow_token)
      }
    }
  }, [item?.id, item?.status, item?.token_escrow])

  const { mutate: saveEdit, isPending } = useMutation({
    mutationFn: (payload) => updateFoundItemByTrackingRef(activeRef, payload),
    onSuccess: (data) => {
      queryClient.setQueryData(['found-track', activeRef], data)
      toast.success('Changes saved')
      saveFoundTrackingRef(data.tracking_reference)
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Could not save changes'),
    onSettled: () => release(),
  })

  function handleLookup(e) {
    e.preventDefault()
    const ref = inputRef.trim().toUpperCase()
    if (!ref) return toast.error('Enter your tracking reference')
    setActiveRef(ref)
    saveFoundTrackingRef(ref)
  }

  async function handleImageSelect(file, idx) {
    const ALLOWED = ['image/jpeg', 'image/png', 'image/webp']
    if (!ALLOWED.includes(file.type)) { toast.error('Only JPEG, PNG, and WEBP images are accepted'); return }
    if (file.size > 5 * 1024 * 1024) { toast.error('Image must be 5 MB or smaller'); return }

    setUploadingIdx(idx)
    setImages((prev) => { const next = [...prev]; next[idx] = { url: null }; return next })
    try {
      const url = await uploadImageToCloudinary(file)
      setImages((prev) => { const next = [...prev]; next[idx] = { url }; return next })
    } catch (err) {
      toast.error(err.message || 'Image upload failed')
      setImages((prev) => { const next = [...prev]; next[idx] = null; return next })
    } finally {
      setUploadingIdx(null)
    }
  }

  function handleSave(e) {
    e.preventDefault()
    if (!item?.can_edit) return
    if (!tryAcquire()) return
    const imageUrls = images.filter((img) => img?.url).map((img) => img.url)
    if (!imageUrls.length) {
      release()
      return toast.error('At least one photo is required')
    }
    saveEdit({
      category: category || undefined,
      public_description: description.trim(),
      image_urls: imageUrls,
    })
  }

  const statusLabel = useMemo(() => {
    if (!item) return ''
    return item.status.replace(/_/g, ' ')
  }, [item])

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <NavBar />
      <div className="max-w-2xl mx-auto px-4 py-10 max-md:py-5">
        <h1 className="text-2xl max-md:text-xl font-bold text-slate-900 dark:text-white mb-2">
          Track My Found Item
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
          Enter the tracking reference from when you reported a found item. No account needed.
        </p>

        <form onSubmit={handleLookup} className="glass p-4 flex flex-col sm:flex-row gap-3 mb-8">
          <input
            type="text"
            value={inputRef}
            onChange={(e) => setInputRef(e.target.value.toUpperCase())}
            placeholder="e.g. A1B2C3D4"
            maxLength={8}
            className="input-field font-mono tracking-widest uppercase flex-1"
          />
          <button type="submit" className="btn-primary sm:min-w-[120px]">
            Look up
          </button>
        </form>

        {isLoading && (
          <p className="text-sm text-slate-500 text-center py-8">Loading…</p>
        )}

        {isError && activeRef && (
          <div className="glass p-6 text-center text-sm text-red-500">
            No item found for reference <span className="font-mono">{activeRef}</span>.
          </div>
        )}

        {item && (
          <div className="space-y-6">
            <div className="glass p-5 border border-brand-200/60 dark:border-brand-800/40">
              <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">Tracking reference</p>
              <p className="text-2xl font-mono font-bold text-brand-700 dark:text-brand-300 tracking-widest">
                {item.tracking_reference}
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-400 mt-3">
                {item.instruction_message}
              </p>
              <p className="text-xs text-slate-500 mt-2 inline-flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5" aria-hidden />
                Drop off at: <strong className="text-slate-700 dark:text-slate-200">{item.drop_point_name}</strong>
              </p>
              <p className="text-xs text-slate-400 mt-2 capitalize">Status: {statusLabel}</p>
            </div>

            <DropOffPanel
              item={item}
              activeRef={activeRef}
              onUpdated={(data) => queryClient.setQueryData(['found-track', activeRef], data)}
              onTokenEscrow={setTokenEscrow}
            />

            <FinderTokenPrompt
              tokenEscrow={promptDismissed ? null : tokenEscrow}
              onDismiss={() => setPromptDismissed(true)}
              onClaimed={() => {
                setPromptDismissed(true)
                setTokenEscrow(null)
              }}
            />

            {item.can_edit ? (
              <form onSubmit={handleSave} className="glass p-6 space-y-5">
                <p className="text-sm text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/20
                                border border-amber-200 dark:border-amber-800 rounded-lg px-3 py-2">
                  You can edit for <strong>{item.minutes_remaining} more minute{item.minutes_remaining !== 1 ? 's' : ''}</strong>
                  {' '}— until the drop point receives the item.
                </p>

                <div>
                  <p className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">Photos</p>
                  <div className="flex gap-3">
                    {images.map((img, idx) => (
                      <ImageUploadSlot
                        key={idx}
                        index={idx}
                        imageUrl={img?.url || null}
                        uploading={uploadingIdx === idx}
                        onSelect={(file) => handleImageSelect(file, idx)}
                        onRemove={() => setImages((prev) => {
                          const next = [...prev]
                          next[idx] = null
                          return next
                        })}
                        className="w-24 h-24"
                      />
                    ))}
                  </div>
                </div>

                <div>
                  <p className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">Category</p>
                  <CategoryPicker value={category} onChange={setCategory} />
                </div>

                <div>
                  <p className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">Description</p>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    rows={3}
                    maxLength={1000}
                    className="input-field resize-none"
                  />
                </div>

                <SubmitButton
                  loading={isSubmitting || isPending}
                  disabled={uploadingIdx !== null}
                  className="btn-primary w-full sm:w-auto"
                  loadingLabel="Saving…"
                >
                  Save changes
                </SubmitButton>
              </form>
            ) : (
              <div className="glass p-6">
                <p className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
                  {getCategoryLabel(item.category)}
                </p>
                <p className="text-sm text-slate-600 dark:text-slate-400">{item.public_description}</p>
                <p className="text-xs text-slate-500 mt-3">
                  Editing is no longer available — the 30-minute window has closed or the item was received.
                </p>
                <button
                  type="button"
                  onClick={() => refetch()}
                  className="text-xs text-brand-600 dark:text-brand-400 hover:underline mt-3"
                >
                  Refresh status
                </button>
              </div>
            )}

            <p className="text-center text-sm text-slate-500">
              <Link to="/report/found" className="text-brand-600 dark:text-brand-400 hover:underline">
                Report another found item
              </Link>
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
