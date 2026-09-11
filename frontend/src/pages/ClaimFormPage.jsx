/**
 * Claim Form — shared by Path A and Path C (Section 8.2).
 */
import { useState, useEffect } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import NavBar from '../components/NavBar'
import ImageUploadSlot from '../components/ImageUploadSlot'
import SubmitButton from '../components/SubmitButton'
import SubmitAccuracyDialog from '../components/SubmitAccuracyDialog'
import { useSubmitLock } from '../hooks/useSubmitLock'
import { useCampusZones } from '../hooks/useCampusZones'
import { getItemDetail, uploadImageToCloudinary } from '../services/itemService'
import { submitClaimPathA, submitClaimPathC } from '../services/claimService'
import { invalidateAfterClaimSubmit } from '../utils/queryCache'
import { getCategoryLabel, ChevronLeft } from '../components/icons'

function ClaimResult({ result, foundItemId }) {
  const isReady = result.collection_phase === 'ready_for_collection'
  return (
    <div className="glass p-6 space-y-4 max-w-lg mx-auto">
      <h2 className="text-lg font-bold text-slate-800 dark:text-slate-100">
        {isReady ? 'Ready for collection' : 'Claim submitted'}
      </h2>
      <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
        {result.message}
      </p>
      {isReady && result.drop_point_name && (
        <div className="text-sm rounded-xl border border-emerald-200 dark:border-emerald-800
                        bg-emerald-50/80 dark:bg-emerald-900/20 p-4 space-y-1">
          <p className="font-semibold text-emerald-800 dark:text-emerald-200">
            {result.drop_point_name}
          </p>
          {result.operating_hours && (
            <p className="text-emerald-700 dark:text-emerald-300">
              Hours: {result.operating_hours}
            </p>
          )}
          <p className="text-emerald-700 dark:text-emerald-300 text-xs mt-2">
            Bring your student ID. An authority will interview you in person before handover.
          </p>
        </div>
      )}
      {!isReady && (
        <p className="text-xs text-slate-500 dark:text-slate-400">
          You will receive a notification when the item arrives at the drop point.
        </p>
      )}
      <div className="flex flex-wrap gap-3 pt-2">
        <Link to={`/items/${foundItemId}`} className="btn-secondary text-sm">
          Back to item
        </Link>
        <Link to={`/claims/status/${result.claim_id}`} className="btn-primary text-sm">
          Check status
        </Link>
        <Link to="/dashboard?tab=pending" className="btn-secondary text-sm">
          View dashboard
        </Link>
      </div>
    </div>
  )
}

export default function ClaimFormPage() {
  const { foundItemId } = useParams()
  const [searchParams] = useSearchParams()
  const path = (searchParams.get('path') || 'c').toLowerCase()
  const isPathA = path === 'a'
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { isSubmitting, tryAcquire, release } = useSubmitLock()
  const { zones, zonesLoading } = useCampusZones()

  const [photoUrl, setPhotoUrl] = useState(null)
  const [uploadingPhoto, setUploadingPhoto] = useState(false)
  const [dateLost, setDateLost] = useState('')
  const [timeLost, setTimeLost] = useState('')
  const [description, setDescription] = useState('')
  const [lostLocation, setLostLocation] = useState('')
  const [result, setResult] = useState(null)
  const [confirmOpen, setConfirmOpen] = useState(false)

  const { data: item, isLoading, isError } = useQuery({
    queryKey: ['item', foundItemId],
    queryFn: () => getItemDetail(foundItemId),
  })

  useEffect(() => {
    if (!item || isPathA) return
    if (['found', 'overdue'].includes(item.status)) {
      navigate(`/items/${foundItemId}/interest`, { replace: true })
    }
  }, [item, isPathA, foundItemId, navigate])

  const { mutate: submitClaim } = useMutation({
    mutationFn: (payload) => (isPathA
      ? submitClaimPathA(foundItemId, payload)
      : submitClaimPathC(foundItemId, payload)),
    onSuccess: (data) => {
      invalidateAfterClaimSubmit(queryClient, { foundItemId })
      setResult(data)
      toast.success('Claim submitted')
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Could not submit claim'),
    onSettled: () => release(),
  })

  async function handlePhotoSelect(file) {
    setUploadingPhoto(true)
    setPhotoUrl(null)
    try {
      const url = await uploadImageToCloudinary(file)
      setPhotoUrl(url)
    } catch {
      toast.error('Photo upload failed')
    } finally {
      setUploadingPhoto(false)
    }
  }

  function handleSubmit(e) {
    e.preventDefault()
    if (!tryAcquire()) return
    if (!isPathA && !lostLocation.trim()) {
      toast.error('Please select where you lost the item')
      release()
      return
    }
    submitClaim({
      photo_url: photoUrl || null,
      date_lost: dateLost,
      time_lost: timeLost,
      description: description.trim(),
      lost_location: isPathA ? null : lostLocation.trim(),
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

  if (isError || !item || item.item_type !== 'found') {
    return (
      <>
        <NavBar />
        <div className="page-container py-16 text-center">
          <p className="text-slate-500">Found item not found.</p>
          <Link to="/found" className="btn-primary text-sm mt-4 inline-block">Browse found items</Link>
        </div>
      </>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <NavBar />
      <div className="page-container py-8 max-w-2xl">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-brand-600 mb-6"
        >
          <ChevronLeft className="w-4 h-4" aria-hidden />
          Back
        </button>

        {result ? (
          <ClaimResult result={result} foundItemId={foundItemId} />
        ) : (
          <>
            <div className="mb-6">
              <p className="text-xs font-bold uppercase tracking-wide text-brand-600 dark:text-brand-400 mb-1">
                {isPathA ? 'Path A — AI match' : 'Path C — This might be mine'}
              </p>
              <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100">
                Claim form
              </h1>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                {getCategoryLabel(item.category)} · {item.public_description.slice(0, 80)}
                {item.public_description.length > 80 ? '…' : ''}
              </p>
            </div>

            <form onSubmit={handleSubmit} className="glass p-6 space-y-5">
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Help the drop point authority verify you are the owner. Include specific details
                only you would know — this is reference material, not an automatic score.
              </p>

              <div>
                <label className="label">Photo of the item (optional)</label>
                <p className="text-xs text-slate-400 mb-2">As you remember it — not required.</p>
                <ImageUploadSlot
                  imageUrl={photoUrl}
                  uploading={uploadingPhoto}
                  onSelect={handlePhotoSelect}
                  onRemove={() => setPhotoUrl(null)}
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="label">Date lost</label>
                  <input
                    type="date"
                    className="input-field w-full"
                    value={dateLost}
                    onChange={(e) => setDateLost(e.target.value)}
                    required
                  />
                </div>
                <div>
                  <label className="label">Approximate time lost</label>
                  <input
                    type="time"
                    className="input-field w-full"
                    value={timeLost}
                    onChange={(e) => setTimeLost(e.target.value)}
                    required
                  />
                </div>
              </div>

              {!isPathA && (
                <div>
                  <label className="label">Where you lost it</label>
                  <select
                    className="input-field w-full"
                    value={lostLocation}
                    onChange={(e) => setLostLocation(e.target.value)}
                    required
                    disabled={zonesLoading}
                  >
                    <option value="">Select campus location…</option>
                    {zones.map((z) => (
                      <option key={z.id} value={z.name}>{z.name}</option>
                    ))}
                  </select>
                </div>
              )}

              <div>
                <label className="label">Your description of the item</label>
                <textarea
                  className="input-field w-full min-h-[120px]"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Unique details only the owner would know — scratches, contents, stickers, etc."
                  required
                  minLength={10}
                />
              </div>

              <SubmitButton loading={isSubmitting} className="btn-primary w-full sm:w-auto">
                Submit claim
              </SubmitButton>
            </form>
          </>
        )}
      </div>
    </div>
  )
}
