/**
 * Feature D / W3 — Report Found Item (no login required).
 */
import { useState, useMemo, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import NavBar from '../components/NavBar'
import ImageUploadSlot from '../components/ImageUploadSlot'
import {
  createFoundItem,
  uploadImageToCloudinary,
} from '../services/itemService'
import { listDropPoints, getNearestDropPoint } from '../services/dropPointService'
import { invalidateAfterItemCreate } from '../utils/queryCache'
import { saveFoundTrackingRef, getItemDetailPath } from '../utils/foundTracking'
import { getEscrowToken, saveEscrowToken } from '../utils/tokenEscrow'
import { useCampusZones } from '../hooks/useCampusZones'
import { MapPin, Check } from '../components/icons'
import CategoryPicker from '../components/CategoryPicker'
import SubmitButton from '../components/SubmitButton'
import { useSubmitLock } from '../hooks/useSubmitLock'

function Field({ label, hint, required, children }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-semibold text-slate-700 dark:text-slate-300">
        {label}
        {required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      {hint && <p className="text-xs text-slate-500 dark:text-slate-400">{hint}</p>}
      {children}
    </div>
  )
}

function SuccessScreen({ result }) {
  return (
    <div className="max-w-2xl mx-auto px-4 py-10 max-md:py-5">
      <div className="glass p-8 max-md:p-5 text-center border border-emerald-200/80 dark:border-emerald-800/50">
        <div className="w-14 h-14 rounded-2xl bg-emerald-100 dark:bg-emerald-900/40
                        flex items-center justify-center mx-auto mb-4 text-emerald-600 dark:text-emerald-400">
          <Check className="w-8 h-8" aria-hidden />
        </div>
        <h1 className="text-2xl max-md:text-xl font-bold text-slate-900 dark:text-white mb-3">
          Report submitted
        </h1>
        <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed mb-6">
          {result.instruction_message}
        </p>

        <div className="bg-slate-100 dark:bg-slate-900/60 rounded-xl p-5 mb-6">
          <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">Your tracking reference</p>
          <p className="text-3xl font-mono font-bold text-brand-700 dark:text-brand-300 tracking-[0.2em]">
            {result.tracking_reference}
          </p>
          <p className="text-xs text-slate-500 mt-2">
            Save this code — we stored it in your browser so you can return without an account.
          </p>
        </div>

        <p className="text-sm text-slate-500 mb-6 inline-flex items-center justify-center gap-1.5">
          <MapPin className="w-4 h-4 shrink-0 text-brand-500" aria-hidden />
          <span>
            Drop off at: <strong className="text-slate-800 dark:text-slate-100">{result.drop_point_name}</strong>
          </span>
        </p>

        {result.drop_off?.qr_payload && (
          <div className="mb-6">
            <p className="text-xs text-slate-500 mb-2">Drop-off QR code (show at the drop point)</p>
            <img
              src={`https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${encodeURIComponent(result.drop_off.qr_payload)}`}
              alt="Drop-off QR code"
              className="mx-auto rounded-lg border border-slate-200 dark:border-slate-700"
              width={180}
              height={180}
            />
          </div>
        )}

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link
            to={getItemDetailPath(result.id)}
            className="btn-primary text-sm text-center text-base py-3 px-6"
          >
            Track My Item
          </Link>
          <Link to="/" className="btn-secondary text-sm text-center">
            Back to home
          </Link>
        </div>
      </div>
    </div>
  )
}

export default function ReportFoundPage() {
  const queryClient = useQueryClient()

  const [category, setCategory]         = useState('')
  const [description, setDescription]   = useState('')
  const [locationId, setLocationId]     = useState('')
  const [dateFound, setDateFound]       = useState('')
  const [timeFound, setTimeFound]       = useState('')
  const [images, setImages]             = useState([null, null])
  const [uploadingIdx, setUploadingIdx] = useState(null)
  const [selectedDropPointId, setSelectedDropPointId] = useState('')
  const [suggestedDropPointId, setSuggestedDropPointId] = useState('')
  const [dropPointOptions, setDropPointOptions] = useState([])
  const [successResult, setSuccessResult] = useState(null)

  const { isSubmitting, tryAcquire, release } = useSubmitLock()
  const todayMax = useMemo(() => new Date().toISOString().split('T')[0], [])
  const { zones, zonesLoading } = useCampusZones()

  const selectedZone = useMemo(
    () => zones.find((z) => String(z.id) === String(locationId)),
    [zones, locationId],
  )

  const universityId = selectedZone?.university_id

  const { data: dropPointsData } = useQuery({
    queryKey: ['drop-points', universityId],
    queryFn: () => listDropPoints(universityId),
    enabled: Boolean(universityId),
    staleTime: 5 * 60_000,
  })

  useEffect(() => {
    if (!selectedZone?.latitude || !selectedZone?.longitude || !universityId) {
      setSuggestedDropPointId('')
      setSelectedDropPointId('')
      setDropPointOptions([])
      return
    }

    let cancelled = false
    getNearestDropPoint({
      lat: selectedZone.latitude,
      lng: selectedZone.longitude,
      universityId,
    })
      .then((data) => {
        if (cancelled) return
        const nearestId = data.nearest?.id
        setSuggestedDropPointId(nearestId || '')
        setSelectedDropPointId(nearestId || '')
        setDropPointOptions(data.alternatives || [])
      })
      .catch(() => {
        if (!cancelled) {
          setSuggestedDropPointId('')
          setSelectedDropPointId('')
          setDropPointOptions(dropPointsData?.drop_points || [])
        }
      })

    return () => { cancelled = true }
  }, [selectedZone?.id, selectedZone?.latitude, selectedZone?.longitude, universityId, dropPointsData])

  const { mutate: submit, isPending } = useMutation({
    mutationFn: createFoundItem,
    onSuccess: (data) => {
      saveFoundTrackingRef(data.tracking_reference, data.id, data.drop_point_name)
      if (data.token_escrow?.escrow_token) {
        saveEscrowToken(data.token_escrow.escrow_token)
      }
      invalidateAfterItemCreate(queryClient, { type: 'found' })
      setSuccessResult(data)
    },
    onError: (err) => {
      const msg = err.response?.data?.detail || 'Failed to submit report. Please try again.'
      toast.error(msg)
    },
    onSettled: () => {
      release()
    },
  })

  async function handleImageSelect(file, idx) {
    const ALLOWED = ['image/jpeg', 'image/png', 'image/webp']
    if (!ALLOWED.includes(file.type)) { toast.error('Only JPEG, PNG, and WEBP images are accepted'); return }
    if (file.size > 5 * 1024 * 1024)  { toast.error('Image must be 5 MB or smaller'); return }

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

  function handleImageRemove(idx) {
    setImages((prev) => {
      const next = [...prev]
      next[idx] = null
      return next
    })
  }

  function handleSubmit(e) {
    e.preventDefault()
    if (!tryAcquire()) return

    if (!category) { release(); return toast.error('Please select a category') }
    if (!description.trim()) { release(); return toast.error('Description is required') }
    if (!locationId) { release(); return toast.error('Please select where you found the item') }
    if (!dateFound) { release(); return toast.error('Date found is required') }
    if (!selectedDropPointId) { release(); return toast.error('Please select a drop-off point') }
    if (uploadingIdx !== null) { release(); return toast.error('Please wait for the image to finish uploading') }

    const imageUrls = images.filter((img) => img?.url).map((img) => img.url)
    if (imageUrls.length === 0) {
      release()
      return toast.error('At least one photo is required for found items')
    }

    const dateOccurred = timeFound ? `${dateFound}T${timeFound}:00` : `${dateFound}T00:00:00`

    const payload = {
      category,
      public_description: description.trim(),
      location_id: locationId,
      date_occurred: dateOccurred,
      image_urls: imageUrls,
    }
    if (selectedDropPointId && selectedDropPointId !== suggestedDropPointId) {
      payload.drop_point_id = selectedDropPointId
    }
    const existingEscrow = getEscrowToken()
    if (existingEscrow) {
      payload.escrow_token = existingEscrow
    }

    submit(payload)
  }

  const hasRequiredImage = images.some((img) => img?.url)

  if (successResult) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
        <NavBar />
        <SuccessScreen result={successResult} />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <NavBar />

      <div className="max-w-2xl mx-auto px-4 py-10 max-md:py-5 overflow-x-hidden">
        <div className="mb-8 max-md:mb-5">
          <h1 className="text-2xl max-md:text-xl font-bold text-slate-900 dark:text-white">
            Report a Found Item
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            No account needed. Tell us what you found, choose a campus drop-off point, and
            bring the item there within 48 hours.
          </p>
          <p className="mt-2 text-xs">
            <Link to="/found" className="text-brand-600 dark:text-brand-400 hover:underline">
              Already reported? Find your item on the Found Items page →
            </Link>
          </p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-7 max-md:gap-5">
          <div className="glass p-6 max-md:p-4">
            <h2 className="section-heading mb-1">Photos <span className="text-red-500">*</span></h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-5">
              At least 1 photo required. Max 2. JPEG, PNG, or WEBP, up to 5 MB each.
            </p>
            <div className="flex gap-4">
              {images.map((img, idx) => (
                <ImageUploadSlot
                  key={idx}
                  index={idx}
                  imageUrl={img?.url || null}
                  uploading={uploadingIdx === idx}
                  required={idx === 0 && !hasRequiredImage}
                  onSelect={(file) => handleImageSelect(file, idx)}
                  onRemove={() => handleImageRemove(idx)}
                />
              ))}
            </div>
            {!hasRequiredImage && (
              <p className="mt-3 text-xs text-red-500 dark:text-red-400">
                Upload at least one photo before submitting.
              </p>
            )}
          </div>

          <div className="glass p-6 max-md:p-4 relative z-[1] overflow-visible">
            <h2 className="section-heading mb-5">Item Details</h2>
            <div className="flex flex-col gap-5">
              <Field label="Category" required hint="Choose the category that best matches your item.">
                <CategoryPicker value={category} onChange={setCategory} />
              </Field>

              <Field label="Description" hint="Describe the item as you found it." required>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                  maxLength={1000}
                  placeholder="e.g. Black Samsung phone with cracked screen protector, found near the ICT lab entrance"
                  className="input-field resize-none"
                  required
                />
                <span className="text-xs text-slate-400 text-right">{description.length}/1000</span>
              </Field>
            </div>
          </div>

          <div className="glass p-6 max-md:p-4">
            <h2 className="section-heading mb-5">Where & When</h2>
            <div className="flex flex-col gap-5">
              <Field label="Campus Location" required hint="Used to suggest the nearest drop-off point.">
                {zonesLoading ? (
                  <div className="input-field text-slate-400">Loading zones…</div>
                ) : (
                  <select
                    value={locationId}
                    onChange={(e) => setLocationId(e.target.value)}
                    className="input-field"
                    required
                  >
                    <option value="">Select location…</option>
                    {zones.map((z) => (
                      <option key={z.id} value={z.id}>{z.name}</option>
                    ))}
                  </select>
                )}
              </Field>

              <div className="grid grid-cols-2 gap-4">
                <Field label="Date Found" required>
                  <input
                    type="date"
                    value={dateFound}
                    max={todayMax}
                    onChange={(e) => setDateFound(e.target.value)}
                    className="input-field"
                    required
                  />
                </Field>
                <Field label="Approximate Time">
                  <input
                    type="time"
                    value={timeFound}
                    onChange={(e) => setTimeFound(e.target.value)}
                    className="input-field"
                  />
                </Field>
              </div>
            </div>
          </div>

          <div className="glass p-6 max-md:p-4">
            <h2 className="section-heading mb-1">Drop-off Point <span className="text-red-500">*</span></h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
              We suggest the nearest campus drop point based on where you found the item.
              You can choose a different one if you prefer.
            </p>

            {!locationId ? (
              <p className="text-sm text-slate-500">Select a campus location first.</p>
            ) : dropPointOptions.length === 0 ? (
              <p className="text-sm text-slate-500">Loading drop points…</p>
            ) : (
              <div className="space-y-2">
                {dropPointOptions.map((dp) => {
                  const isSuggested = dp.id === suggestedDropPointId
                  const isSelected = dp.id === selectedDropPointId
                  return (
                    <label
                      key={dp.id}
                      className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-colors
                        ${isSelected
                          ? 'border-brand-500 bg-brand-50/80 dark:bg-brand-900/20'
                          : 'border-slate-200 dark:border-slate-700 hover:border-brand-300'
                        }`}
                    >
                      <input
                        type="radio"
                        name="drop_point"
                        value={dp.id}
                        checked={isSelected}
                        onChange={() => setSelectedDropPointId(dp.id)}
                        className="mt-1"
                      />
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-slate-800 dark:text-slate-100">
                          {dp.name}
                          {isSuggested && (
                            <span className="ml-2 text-[10px] font-semibold uppercase tracking-wide
                                               text-brand-600 dark:text-brand-400">
                              Nearest
                            </span>
                          )}
                        </p>
                        <p className="text-xs text-slate-500 capitalize mt-0.5">
                          {dp.type}
                          {dp.distance_km != null && (
                            <> · {dp.distance_km} km away</>
                          )}
                          {' · '}{dp.operating_hours}
                        </p>
                      </div>
                    </label>
                  )
                })}
              </div>
            )}
          </div>

          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800
                          rounded-xl p-4 text-xs text-blue-800 dark:text-blue-300">
            <strong>Next step:</strong> After submitting, take the item to your chosen drop point
            within 48 hours. You&apos;ll get a tracking reference to manage this report without logging in.
          </div>

          <div className="flex gap-3 justify-end">
            <Link to="/" className="btn-secondary">
              Cancel
            </Link>
            <SubmitButton
              loading={isSubmitting || isPending}
              disabled={uploadingIdx !== null || !hasRequiredImage || !locationId || !selectedDropPointId}
              className="btn-primary min-w-[140px] mobile-form-submit md:w-auto"
              loadingLabel="Submitting…"
            >
              Submit Report
            </SubmitButton>
          </div>
        </form>
      </div>
    </div>
  )
}
