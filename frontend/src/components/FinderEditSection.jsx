/**
 * Finder 30-minute edit window — photos, category, description (Section 7.4).
 */
import { useState, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import CategoryPicker from './CategoryPicker'
import ImageUploadSlot from './ImageUploadSlot'
import SubmitButton from './SubmitButton'
import { useSubmitLock } from '../hooks/useSubmitLock'
import {
  updateFoundItemByTrackingRef,
  updateFoundItem,
  uploadImageToCloudinary,
} from '../services/itemService'
import { saveFoundTrackingRef } from '../utils/foundTracking'

export default function FinderEditSection({
  itemId,
  trackingRef,
  trackData,
  onUpdated,
}) {
  const { isSubmitting, tryAcquire, release } = useSubmitLock()
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState('')
  const [images, setImages] = useState([null, null])
  const [uploadingIdx, setUploadingIdx] = useState(null)

  useEffect(() => {
    if (!trackData) return
    setDescription(trackData.public_description || '')
    setCategory(trackData.category || '')
    const slots = [null, null]
    ;(trackData.image_urls || []).slice(0, 2).forEach((url, i) => {
      slots[i] = { url }
    })
    setImages(slots)
  }, [trackData?.id, trackData?.public_description, trackData?.category, trackData?.image_urls])

  const { mutate: saveEdit, isPending } = useMutation({
    mutationFn: async (payload) => {
      if (trackingRef) {
        return updateFoundItemByTrackingRef(trackingRef, payload)
      }
      return updateFoundItem(itemId, payload)
    },
    onSuccess: (data) => {
      if (data.tracking_reference) {
        saveFoundTrackingRef(data.tracking_reference, data.id, data.drop_point_name)
      }
      onUpdated?.(data)
      toast.success('Changes saved')
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Could not save changes'),
    onSettled: () => release(),
  })

  async function handleImageSelect(file, idx) {
    const ALLOWED = ['image/jpeg', 'image/png', 'image/webp']
    if (!ALLOWED.includes(file.type)) {
      toast.error('Only JPEG, PNG, and WEBP images are accepted')
      return
    }
    if (file.size > 5 * 1024 * 1024) {
      toast.error('Image must be 5 MB or smaller')
      return
    }

    setUploadingIdx(idx)
    setImages((prev) => {
      const next = [...prev]
      next[idx] = { url: null }
      return next
    })
    try {
      const url = await uploadImageToCloudinary(file)
      setImages((prev) => {
        const next = [...prev]
        next[idx] = { url }
        return next
      })
    } catch (err) {
      toast.error(err.message || 'Image upload failed')
      setImages((prev) => {
        const next = [...prev]
        next[idx] = null
        return next
      })
    } finally {
      setUploadingIdx(null)
    }
  }

  function handleSave(e) {
    e.preventDefault()
    if (!trackData?.can_edit) return
    if (!tryAcquire()) return
    const imageUrls = images.filter((img) => img?.url).map((img) => img.url)
    if (!imageUrls.length) {
      release()
      toast.error('At least one photo is required')
      return
    }
    saveEdit({
      category: category || undefined,
      public_description: description.trim(),
      image_urls: imageUrls,
    })
  }

  if (!trackData?.can_edit) return null

  return (
    <form onSubmit={handleSave} className="mb-6 glass p-5 space-y-4 border border-amber-200/50 dark:border-amber-800/40">
      <h2 className="text-sm font-bold text-slate-800 dark:text-slate-100">
        Edit your report
      </h2>
      <p className="text-sm text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/20
                      border border-amber-200 dark:border-amber-800 rounded-lg px-3 py-2">
        You can edit for{' '}
        <strong>{trackData.minutes_remaining} more minute{trackData.minutes_remaining !== 1 ? 's' : ''}</strong>
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
          className="input-field resize-none w-full"
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
  )
}
