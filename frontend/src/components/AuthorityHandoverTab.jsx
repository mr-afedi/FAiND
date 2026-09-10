/**
 * Authority Handover tab — Section 11 (W10).
 */
import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { getCategoryLabel, Camera, X } from './icons'
import { Handshake, Clock, CheckCircle } from 'lucide-react'
import SubmitButton from './SubmitButton'
import { useSubmitLock } from '../hooks/useSubmitLock'
import { uploadImageToCloudinary } from '../services/itemService'
import {
  getAuthorityHandoverQueue,
  getAuthorityHandover,
  startAuthorityHandover,
  overrideAuthorityHandover,
} from '../services/authorityService'
import { useAuthorityLightbox } from '../context/AuthorityLightboxContext'
import { LightboxImage } from './ImageLightbox'
import { optimizeCloudinaryUrl } from '../utils/cloudinary'
import { invalidateAfterHandover } from '../utils/queryCache'
import HandoverWizardMobile from './staff-mobile/HandoverWizardMobile'
import StaffMobileBottomSheet from './staff-mobile/StaffMobileBottomSheet'
import StaffDesktopDetailModal from './staff-mobile/StaffDesktopDetailModal'

function ConditionPhotoSlot({ imageUrl, uploading, onSelect, onRemove, onImageOpen }) {
  const inputRef = useRef(null)
  return (
    <div
      className="relative w-full aspect-video max-h-48 rounded-xl border-2 border-dashed
                 border-slate-600 overflow-hidden flex items-center justify-center cursor-pointer bg-black/20"
      onClick={() => !imageUrl && !uploading && inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={(e) => e.target.files[0] && onSelect(e.target.files[0])}
      />
      {uploading ? (
        <div className="absolute inset-0 bg-slate-800 animate-pulse flex flex-col items-center justify-center gap-2">
          <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-[10px] text-slate-400">Uploading…</span>
        </div>
      ) : imageUrl ? (
        <>
          <LightboxImage
            src={optimizeCloudinaryUrl(imageUrl)}
            images={[optimizeCloudinaryUrl(imageUrl)]}
            index={0}
            onOpen={onImageOpen}
            className="w-full h-full"
          />
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onRemove() }}
            className="absolute top-2 right-2 bg-red-600 text-white rounded-full w-6 h-6 flex items-center justify-center"
          >
            <X className="w-3 h-3" aria-hidden />
          </button>
        </>
      ) : (
        <div className="text-center text-slate-400 text-xs p-4">
          <Camera className="w-8 h-8 mx-auto mb-2" aria-hidden />
          Tap to capture item condition
        </div>
      )}
    </div>
  )
}

function HandoverStartForm({ item, onSuccess, onCancel, onImageOpen }) {
  const { isSubmitting, tryAcquire, release } = useSubmitLock()
  const [conditionUrl, setConditionUrl] = useState(null)
  const [claimantPhotoUrl, setClaimantPhotoUrl] = useState(null)
  const [uploadingCondition, setUploadingCondition] = useState(false)
  const [uploadingClaimant, setUploadingClaimant] = useState(false)
  const [name, setName] = useState(item.claimant_name || '')
  const [phone, setPhone] = useState('')
  const [studentId, setStudentId] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})

  async function uploadPhoto(file, setter, loadingSetter) {
    loadingSetter(true)
    setter(null)
    try {
      const url = await uploadImageToCloudinary(file)
      setter(url)
    } catch {
      toast.error('Photo upload failed')
    } finally {
      loadingSetter(false)
    }
  }

  const { mutate: startHandover } = useMutation({
    mutationFn: (payload) => startAuthorityHandover(item.claim_id, payload),
    onSuccess: (data) => {
      toast.success(data.message)
      onSuccess(data)
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Could not start handover'),
    onSettled: () => release(),
  })

  function handleSubmit(e) {
    e.preventDefault()
    if (!tryAcquire()) return
    if (uploadingCondition || uploadingClaimant) {
      toast.error('Please wait for photo uploads to finish')
      release()
      return
    }
    const errs = {}
    if (!conditionUrl) errs.condition_photo = 'Condition photo is required'
    if (!name.trim()) errs.claimant_name = 'Claimant name is required'
    if (!phone.trim()) errs.claimant_phone = 'Phone number is required'
    if (!studentId.trim()) errs.claimant_student_id = 'Student ID is required'
    if (!claimantPhotoUrl) errs.claimant_photo = 'Claimant photo is required'
    if (Object.keys(errs).length) {
      setFieldErrors(errs)
      release()
      return
    }
    setFieldErrors({})
    startHandover({
      condition_photo_url: conditionUrl,
      claimant_name: name.trim(),
      claimant_phone: phone.trim(),
      claimant_student_id: studentId.trim(),
      claimant_photo_url: claimantPhotoUrl,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="hidden md:block glass p-5 space-y-4 border border-slate-800/80">
      <div>
        <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Verify and Hand Over</h3>
        <p className="text-xs text-slate-500 mt-1">
          {getCategoryLabel(item.found_item_category)} · {item.found_item_description.slice(0, 60)}
        </p>
      </div>

      <div>
        <label className="label">Item condition at handover <span className="text-red-400">*</span></label>
        <ConditionPhotoSlot
          imageUrl={conditionUrl}
          uploading={uploadingCondition}
          onSelect={(f) => uploadPhoto(f, setConditionUrl, setUploadingCondition)}
          onRemove={() => { setConditionUrl(null); setFieldErrors((e) => ({ ...e, condition_photo: undefined })) }}
          onImageOpen={onImageOpen}
        />
        {fieldErrors.condition_photo && <p className="error-text">{fieldErrors.condition_photo}</p>}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="label">Claimant name <span className="text-red-400">*</span></label>
          <input
            className="input-field w-full"
            value={name}
            onChange={(e) => { setName(e.target.value); setFieldErrors((er) => ({ ...er, claimant_name: undefined })) }}
            required
          />
          {fieldErrors.claimant_name && <p className="error-text">{fieldErrors.claimant_name}</p>}
        </div>
        <div>
          <label className="label">Phone number <span className="text-red-400">*</span></label>
          <input
            className="input-field w-full"
            value={phone}
            onChange={(e) => { setPhone(e.target.value); setFieldErrors((er) => ({ ...er, claimant_phone: undefined })) }}
            required
          />
          {fieldErrors.claimant_phone && <p className="error-text">{fieldErrors.claimant_phone}</p>}
        </div>
        <div className="sm:col-span-2">
          <label className="label">Student ID <span className="text-red-400">*</span></label>
          <input
            className="input-field w-full"
            value={studentId}
            onChange={(e) => { setStudentId(e.target.value); setFieldErrors((er) => ({ ...er, claimant_student_id: undefined })) }}
            required
          />
          {fieldErrors.claimant_student_id && <p className="error-text">{fieldErrors.claimant_student_id}</p>}
        </div>
      </div>

      <div>
        <label className="label">Claimant photo <span className="text-red-400">*</span></label>
        <ConditionPhotoSlot
          imageUrl={claimantPhotoUrl}
          uploading={uploadingClaimant}
          onSelect={(f) => uploadPhoto(f, setClaimantPhotoUrl, setUploadingClaimant)}
          onRemove={() => { setClaimantPhotoUrl(null); setFieldErrors((e) => ({ ...e, claimant_photo: undefined })) }}
          onImageOpen={onImageOpen}
        />
        {fieldErrors.claimant_photo && <p className="error-text">{fieldErrors.claimant_photo}</p>}
      </div>

      <div className="flex flex-wrap gap-2">
        <SubmitButton loading={isSubmitting} className="btn-primary text-sm">
          Submit handover
        </SubmitButton>
        <button type="button" onClick={onCancel} className="btn-secondary text-sm">
          Cancel
        </button>
      </div>
    </form>
  )
}

function AwaitingOwnerCard({ item, onOverride, overriding, onImageOpen }) {
  const [note, setNote] = useState('')
  const [showOverride, setShowOverride] = useState(false)

  function handleOverride(e) {
    e.preventDefault()
    if (note.trim().length < 10) {
      toast.error('Override note must be at least 10 characters')
      return
    }
    onOverride(item.handover_id, note.trim())
  }

  return (
    <article className="glass p-5 space-y-3 border border-amber-800/50">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs text-amber-400 uppercase tracking-wide font-bold">Awaiting owner confirmation</p>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100 mt-1">{item.claimant_name}</h3>
          <p className="text-xs text-slate-500 mt-1">{item.found_item_description}</p>
        </div>
      </div>

      {item.condition_photo_url && (
        <LightboxImage
          src={item.condition_photo_url}
          images={[item.condition_photo_url]}
          index={0}
          onOpen={onImageOpen}
          className="w-full max-h-40 rounded-lg overflow-hidden border border-slate-700 bg-black/30"
        />
      )}

      <p className="text-xs text-slate-400">
        The owner has been notified to confirm digitally on their device.
      </p>

      {!showOverride ? (
        <button
          type="button"
          onClick={() => setShowOverride(true)}
          className="text-xs text-amber-400 hover:text-amber-300 underline"
        >
          Owner can&apos;t confirm digitally — override
        </button>
      ) : (
        <form onSubmit={handleOverride} className="space-y-2 border-t border-slate-800 pt-3">
          <label className="label text-amber-300">Override note (required, flagged for Root Admin)</label>
          <textarea
            className="input-field w-full min-h-[80px] text-sm"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="e.g. Owner confirmed verbally but could not use the app on the spot"
            required
            minLength={10}
          />
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={overriding}
              className="btn-primary text-xs py-2"
            >
              {overriding ? 'Completing…' : 'Complete without digital sign-off'}
            </button>
            <button
              type="button"
              onClick={() => setShowOverride(false)}
              className="btn-secondary text-xs py-2"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </article>
  )
}

function CompletedCard({ item, onSelect, selected }) {
  return (
    <article
      role="button"
      tabIndex={0}
      onClick={() => item.handover_id && onSelect(item.handover_id)}
      onKeyDown={(e) => {
        if ((e.key === 'Enter' || e.key === ' ') && item.handover_id) {
          e.preventDefault()
          onSelect(item.handover_id)
        }
      }}
      className={`glass rounded-2xl p-4 md:p-5 border cursor-pointer transition-colors
        ${selected ? 'border-brand-500/60 ring-1 ring-brand-500/30' : 'border-emerald-800/40 hover:border-emerald-700/60'}`}
    >
      <p className="text-sm text-emerald-400 uppercase tracking-wide font-bold flex items-center gap-1.5">
        <CheckCircle className="w-4 h-4" aria-hidden />
        Handover complete
      </p>
      <h3 className="text-base md:text-sm font-semibold text-slate-900 dark:text-slate-100 mt-1">{item.claimant_name}</h3>
      <p className="text-base md:text-xs text-slate-500 mt-1 line-clamp-2">{item.found_item_description}</p>
      <p className="text-sm md:text-xs text-slate-400 mt-2 flex items-center gap-1.5">
        <Clock className="w-4 h-4 shrink-0" aria-hidden />
        {item.authority_override
          ? 'Completed via authority override'
          : item.owner_confirmed
            ? 'Owner confirmed digitally'
            : 'Returned'}
        {item.completed_at && (
          <> · {new Date(item.completed_at).toLocaleString()}</>
        )}
      </p>
      <p className="text-sm text-brand-400 mt-2 md:text-[11px]">Tap for full details</p>
    </article>
  )
}

function HandoverDetailContent({ data, onImageOpen }) {
  if (!data) return null
  return (
    <div className="space-y-4 text-base leading-relaxed">
      <div>
        <p className="text-sm text-slate-500 uppercase">{getCategoryLabel(data.found_item_category)}</p>
        <p className="text-slate-900 dark:text-slate-100 font-medium mt-1">{data.found_item_description}</p>
        {data.found_item_location_label && (
          <p className="text-sm text-slate-400 mt-1">Found at {data.found_item_location_label}</p>
        )}
      </div>

      {(data.found_item_image_urls || []).length > 0 && (
        <div className="flex flex-wrap gap-2">
          {data.found_item_image_urls.map((url, i) => (
            <LightboxImage
              key={url}
              src={url}
              images={data.found_item_image_urls}
              index={i}
              onOpen={onImageOpen}
              className="w-20 h-20 rounded-lg overflow-hidden border border-slate-700"
            />
          ))}
        </div>
      )}

      <div className="space-y-1 text-sm text-slate-400">
        <p>Owner: <span className="text-slate-800 dark:text-slate-200">{data.owner_display_name || '—'}</span></p>
        <p>Finder: <span className="text-slate-800 dark:text-slate-200">{data.finder_display_name || 'Anonymous'}</span></p>
        <p>Drop point: <span className="text-slate-800 dark:text-slate-200">{data.drop_point_name || '—'}</span></p>
        <p>Completed: <span className="text-slate-800 dark:text-slate-200">{data.completed_at ? new Date(data.completed_at).toLocaleString() : '—'}</span></p>
      </div>

      <div className="border-t border-slate-800 pt-3 space-y-2 text-sm">
        <p className="text-slate-400 uppercase tracking-wide text-xs">Claimant at handover</p>
        <p>Name: <span className="text-slate-800 dark:text-slate-200">{data.claimant_name}</span></p>
        <p>Phone: <span className="text-slate-800 dark:text-slate-200">{data.claimant_phone}</span></p>
        {data.claimant_student_id && (
          <p>Student ID: <span className="text-slate-800 dark:text-slate-200">{data.claimant_student_id}</span></p>
        )}
        <div className="flex flex-wrap gap-2 mt-2">
          {data.condition_photo_url && (
            <LightboxImage
              src={data.condition_photo_url}
              images={[data.condition_photo_url]}
              index={0}
              onOpen={onImageOpen}
              className="w-28 h-28 rounded-lg overflow-hidden border border-slate-700"
            />
          )}
          {data.claimant_photo_url && (
            <LightboxImage
              src={data.claimant_photo_url}
              images={[data.claimant_photo_url]}
              index={0}
              onOpen={onImageOpen}
              className="w-28 h-28 rounded-lg overflow-hidden border border-slate-700"
            />
          )}
        </div>
      </div>
    </div>
  )
}

function HandoverDetailPanel({ handoverId, onClose, onImageOpen }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['authority-handover-detail', handoverId],
    queryFn: () => getAuthorityHandover(handoverId),
    enabled: Boolean(handoverId),
  })

  if (!handoverId) return null

  return (
    <StaffDesktopDetailModal
      open
      onClose={onClose}
      title="Completed handover details"
    >
      {isLoading && (
        <div className="flex justify-center py-12">
          <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )}
      {isError && <p className="text-sm text-red-400">Could not load handover details.</p>}
      {data && <HandoverDetailContent data={data} onImageOpen={onImageOpen} />}
    </StaffDesktopDetailModal>
  )
}

function HandoverDetailSheet({ handoverId, onClose, onImageOpen }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['authority-handover-detail', handoverId],
    queryFn: () => getAuthorityHandover(handoverId),
    enabled: Boolean(handoverId),
  })

  return (
    <StaffMobileBottomSheet
      open={Boolean(handoverId)}
      onClose={onClose}
      title="Handover details"
    >
      {isLoading && (
        <div className="flex justify-center py-12">
          <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )}
      {isError && <p className="text-base text-red-400">Could not load handover details.</p>}
      {data && <HandoverDetailContent data={data} onImageOpen={onImageOpen} />}
    </StaffMobileBottomSheet>
  )
}

export default function AuthorityHandoverTab() {
  const queryClient = useQueryClient()
  const openLightbox = useAuthorityLightbox()
  const [startingClaimId, setStartingClaimId] = useState(null)
  const [overridingId, setOverridingId] = useState(null)
  const [selectedHandoverId, setSelectedHandoverId] = useState(null)

  const { data, isLoading } = useQuery({
    queryKey: ['authority-handover-queue'],
    queryFn: getAuthorityHandoverQueue,
  })

  const { mutate: overrideHandover } = useMutation({
    mutationFn: ({ handoverId, note }) => overrideAuthorityHandover(handoverId, note),
    onMutate: ({ handoverId }) => setOverridingId(handoverId),
    onSuccess: () => {
      toast.success('Handover completed')
      invalidateAfterHandover(queryClient)
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Override failed'),
    onSettled: () => setOverridingId(null),
  })

  const items = data?.items || []
  const activeItems = items.filter((item) => item.queue_status !== 'completed')
  const completedItems = items.filter((item) => item.queue_status === 'completed')

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (activeItems.length === 0 && completedItems.length === 0) {
    return (
      <div className="glass p-8 text-center">
        <p className="text-sm text-slate-400">No verified claims ready for handover.</p>
        <p className="text-xs text-slate-500 mt-2">Verify a claimant in the Claims tab first.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6 md:max-h-[calc(100vh-10rem)] md:overflow-y-auto md:pr-1">
      {activeItems.length > 0 && (
        <div className="space-y-4">
          {activeItems.map((item) => {
        if (startingClaimId === item.claim_id && item.queue_status === 'ready_to_start') {
          return (
            <div key={item.claim_id}>
              <HandoverWizardMobile
                item={item}
                onImageOpen={openLightbox}
                onSuccess={() => {
                  setStartingClaimId(null)
                  invalidateAfterHandover(queryClient, { foundItemId: item.found_item_id })
                }}
                onCancel={() => setStartingClaimId(null)}
              />
              <HandoverStartForm
                item={item}
                onImageOpen={openLightbox}
                onSuccess={() => {
                  setStartingClaimId(null)
                  invalidateAfterHandover(queryClient, { foundItemId: item.found_item_id })
                }}
                onCancel={() => setStartingClaimId(null)}
              />
            </div>
          )
        }

        if (item.queue_status === 'ready_to_start') {
          return (
            <article key={item.claim_id} className="glass rounded-2xl p-4 md:p-5 border border-slate-800/80 space-y-3">
              <div>
                <p className="text-sm text-slate-500 uppercase flex items-center gap-1.5">
                  <Handshake className="w-4 h-4" aria-hidden />
                  {getCategoryLabel(item.found_item_category)}
                </p>
                <h3 className="text-base md:text-sm font-semibold text-slate-900 dark:text-slate-100 mt-1">{item.claimant_name}</h3>
                <p className="text-base md:text-xs text-slate-500 mt-1 line-clamp-2">{item.found_item_description}</p>
              </div>
              <button
                type="button"
                onClick={() => setStartingClaimId(item.claim_id)}
                className="btn-primary w-full md:w-auto min-h-[48px] text-base md:text-sm"
              >
                Verify and Hand Over
              </button>
            </article>
          )
        }

        if (item.queue_status === 'awaiting_owner') {
          return (
            <AwaitingOwnerCard
              key={item.claim_id}
              item={item}
              overriding={overridingId === item.handover_id}
              onImageOpen={openLightbox}
              onOverride={(handoverId, note) => overrideHandover({ handoverId, note })}
            />
          )
        }

        return null
      })}
        </div>
      )}

      {completedItems.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Completed handovers ({completedItems.length})
          </h3>
          <div className="space-y-3">
            {completedItems.map((item) => (
              <CompletedCard
                key={item.handover_id || item.claim_id}
                item={item}
                onSelect={setSelectedHandoverId}
                selected={selectedHandoverId === item.handover_id}
              />
            ))}
          </div>
        </div>
      )}

      {selectedHandoverId && (
        <>
          <HandoverDetailPanel
            handoverId={selectedHandoverId}
            onClose={() => setSelectedHandoverId(null)}
            onImageOpen={openLightbox}
          />
          <HandoverDetailSheet
            handoverId={selectedHandoverId}
            onClose={() => setSelectedHandoverId(null)}
            onImageOpen={openLightbox}
          />
        </>
      )}
    </div>
  )
}
