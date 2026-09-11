/**
 * Mobile wizard for handover capture (authority dashboard).
 */
import { useState, useRef } from 'react'
import { useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Camera, ChevronLeft, ChevronRight, CheckCircle } from 'lucide-react'
import { getCategoryLabel } from '../icons'
import SubmitButton from '../SubmitButton'
import { useSubmitLock } from '../../hooks/useSubmitLock'
import { uploadImageToCloudinary } from '../../services/itemService'
import { startAuthorityHandover } from '../../services/authorityService'
import { LightboxImage } from '../ImageLightbox'
import { optimizeCloudinaryUrl } from '../../utils/cloudinary'

const STEPS = 5

function MobilePhotoCapture({ label, imageUrl, uploading, onSelect, onRemove, onImageOpen }) {
  const inputRef = useRef(null)
  return (
    <div className="space-y-4">
      <p className="text-base text-slate-700 dark:text-slate-300 leading-relaxed">{label}</p>
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        capture="environment"
        className="hidden"
        onChange={(e) => e.target.files?.[0] && onSelect(e.target.files[0])}
      />
      {uploading ? (
        <div className="w-full aspect-[4/3] rounded-2xl bg-slate-800 animate-pulse
                        flex flex-col items-center justify-center gap-3">
          <div className="w-10 h-10 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm text-slate-400">Uploading…</span>
        </div>
      ) : imageUrl ? (
        <div className="relative w-full aspect-[4/3] rounded-2xl overflow-hidden border border-slate-700">
          <LightboxImage
            src={optimizeCloudinaryUrl(imageUrl)}
            images={[optimizeCloudinaryUrl(imageUrl)]}
            index={0}
            onOpen={onImageOpen}
            className="w-full h-full"
          />
          <button
            type="button"
            onClick={onRemove}
            className="absolute bottom-3 right-3 btn-secondary text-sm min-h-[48px] px-4"
          >
            Retake
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="w-full min-h-[160px] rounded-2xl border-2 border-dashed border-brand-600/60
                     bg-brand-950/30 flex flex-col items-center justify-center gap-3
                     text-brand-300 active:bg-brand-950/50"
        >
          <Camera className="w-12 h-12" strokeWidth={1.5} aria-hidden />
          <span className="text-base font-semibold">Tap to take photo</span>
        </button>
      )}
    </div>
  )
}

export default function HandoverWizardMobile({ item, onSuccess, onCancel, onImageOpen }) {
  const { isSubmitting, tryAcquire, release } = useSubmitLock()
  const [step, setStep] = useState(1)
  const [conditionUrl, setConditionUrl] = useState(null)
  const [claimantPhotoUrl, setClaimantPhotoUrl] = useState(null)
  const [uploadingCondition, setUploadingCondition] = useState(false)
  const [uploadingClaimant, setUploadingClaimant] = useState(false)
  const [name, setName] = useState(item.claimant_name || '')
  const [phone, setPhone] = useState('')
  const [studentId, setStudentId] = useState('')

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

  function canAdvance() {
    if (step === 1) return Boolean(conditionUrl) && !uploadingCondition
    if (step === 2) return Boolean(claimantPhotoUrl) && !uploadingClaimant
    if (step === 3) return name.trim() && phone.trim()
    if (step === 4) return studentId.trim()
    return true
  }

  function handleNext() {
    if (!canAdvance()) {
      toast.error('Please complete this step first')
      return
    }
    if (step < STEPS) setStep((s) => s + 1)
    else handleSubmit()
  }

  function handleSubmit() {
    if (!tryAcquire()) return
    startHandover({
      condition_photo_url: conditionUrl,
      claimant_name: name.trim(),
      claimant_phone: phone.trim(),
      claimant_student_id: studentId.trim(),
      claimant_photo_url: claimantPhotoUrl,
    })
  }

  return (
    <div className="md:hidden space-y-5">
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm text-slate-400">
          <span>Step {step} of {STEPS}</span>
          <button type="button" onClick={onCancel} className="text-slate-500 min-h-[44px] px-2">
            Cancel
          </button>
        </div>
        <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden">
          <div
            className="h-full bg-brand-500 transition-all duration-300"
            style={{ width: `${(step / STEPS) * 100}%` }}
          />
        </div>
        <p className="text-sm text-slate-500">
          {getCategoryLabel(item.found_item_category)} · {item.claimant_name}
        </p>
      </div>

      {step === 1 && (
        <MobilePhotoCapture
          label="Take a photo of the item's current condition"
          imageUrl={conditionUrl}
          uploading={uploadingCondition}
          onSelect={(f) => uploadPhoto(f, setConditionUrl, setUploadingCondition)}
          onRemove={() => setConditionUrl(null)}
          onImageOpen={onImageOpen}
        />
      )}

      {step === 2 && (
        <MobilePhotoCapture
          label="Take a photo of the claimant"
          imageUrl={claimantPhotoUrl}
          uploading={uploadingClaimant}
          onSelect={(f) => uploadPhoto(f, setClaimantPhotoUrl, setUploadingClaimant)}
          onRemove={() => setClaimantPhotoUrl(null)}
          onImageOpen={onImageOpen}
        />
      )}

      {step === 3 && (
        <div className="space-y-4">
          <div>
            <label className="label text-base">Claimant name</label>
            <input
              className="input-field w-full text-base min-h-[48px]"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="label text-base">Phone number</label>
            <input
              type="tel"
              className="input-field w-full text-base min-h-[48px]"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              required
            />
          </div>
        </div>
      )}

      {step === 4 && (
        <div>
          <label className="label text-base">Student ID</label>
          <input
            className="input-field w-full text-base min-h-[48px]"
            value={studentId}
            onChange={(e) => setStudentId(e.target.value)}
            required
          />
        </div>
      )}

      {step === 5 && (
        <div className="space-y-4 text-base text-slate-700 dark:text-slate-300">
          <p className="flex items-center gap-2 text-emerald-400 font-semibold">
            <CheckCircle className="w-5 h-5" aria-hidden />
            Review before submitting
          </p>
          <p><span className="text-slate-500">Name:</span> {name}</p>
          <p><span className="text-slate-500">Phone:</span> {phone}</p>
          <p><span className="text-slate-500">Student ID:</span> {studentId}</p>
          <p><span className="text-slate-500">Photos:</span> Condition + claimant captured</p>
        </div>
      )}

      <div className="flex gap-3 pt-2">
        {step > 1 && (
          <button
            type="button"
            onClick={() => setStep((s) => s - 1)}
            className="btn-secondary flex-1 min-h-[48px] text-base inline-flex items-center justify-center gap-2"
          >
            <ChevronLeft className="w-5 h-5" aria-hidden />
            Back
          </button>
        )}
        <SubmitButton
          type="button"
          onClick={handleNext}
          loading={isSubmitting && step === STEPS}
          disabled={!canAdvance()}
          className="btn-primary flex-1 min-h-[48px] text-base inline-flex items-center justify-center gap-2"
        >
          {step === STEPS ? 'Submit handover' : (
            <>
              Next
              <ChevronRight className="w-5 h-5" aria-hidden />
            </>
          )}
        </SubmitButton>
      </div>
    </div>
  )
}
