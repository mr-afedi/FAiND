/**
 * Item API service — Lost Item Reporting (Feature C).
 * Cloudinary upload handled here for images before form submission.
 */
import api from './api'

const CLOUDINARY_CLOUD = import.meta.env.VITE_CLOUDINARY_CLOUD_NAME
const CLOUDINARY_PRESET = import.meta.env.VITE_CLOUDINARY_UPLOAD_PRESET

// ── Cloudinary upload ─────────────────────────────────────────────────────────

/**
 * Upload a single image file to Cloudinary via unsigned upload preset.
 * Returns the secure_url on success.
 * Section 30.6: only JPEG, PNG, WEBP, max 5 MB.
 */
export async function uploadImageToCloudinary(file) {
  if (!CLOUDINARY_CLOUD || !CLOUDINARY_PRESET) {
    throw new Error(
      'Cloudinary is not configured. Set VITE_CLOUDINARY_CLOUD_NAME and VITE_CLOUDINARY_UPLOAD_PRESET in .env.'
    )
  }

  const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp']
  if (!ALLOWED_TYPES.includes(file.type)) {
    throw new Error('Only JPEG, PNG, and WEBP images are accepted')
  }
  if (file.size > 5 * 1024 * 1024) {
    throw new Error('Image must be 5 MB or smaller')
  }

  const formData = new FormData()
  formData.append('file', file)
  formData.append('upload_preset', CLOUDINARY_PRESET)
  formData.append('folder', 'faind/items')

  const res = await fetch(
    `https://api.cloudinary.com/v1_1/${CLOUDINARY_CLOUD}/image/upload`,
    { method: 'POST', body: formData }
  )

  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err?.error?.message || 'Image upload failed')
  }

  const data = await res.json()
  return data.secure_url
}

// ── Campus zones ──────────────────────────────────────────────────────────────

export async function getCampusZones() {
  const { data } = await api.get('/items/campus-zones')
  return data
}

// ── Lost item CRUD ────────────────────────────────────────────────────────────

export async function createLostItem(payload) {
  const { data } = await api.post('/items/lost', payload)
  return data
}

export async function getMyLostItems({ skip = 0, limit = 20 } = {}) {
  const { data } = await api.get('/items/my/lost', { params: { skip, limit } })
  return data
}

export async function getItemDetail(itemId) {
  const { data } = await api.get(`/items/${itemId}`)
  return data
}

export async function updateItem(itemId, payload) {
  const { data } = await api.patch(`/items/${itemId}`, payload)
  return data
}

export async function deleteItem(itemId) {
  await api.delete(`/items/${itemId}`)
}

export async function extendItem(itemId) {
  const { data } = await api.post(`/items/${itemId}/extend`)
  return data
}

// ── Found item API (Feature D) ────────────────────────────────────────────────

export async function createFoundItem(payload) {
  const { data } = await api.post('/items/found', payload)
  return data
}

export async function getMyFoundItems({ skip = 0, limit = 20 } = {}) {
  const { data } = await api.get('/items/my/found', { params: { skip, limit } })
  return data
}

export async function deleteFoundItem(itemId) {
  await api.delete(`/items/found/${itemId}`)
}

export async function extendFoundItem(itemId) {
  const { data } = await api.post(`/items/found/${itemId}/extend`)
  return data
}

// ── Public Browse (Feature F) — no auth required ──────────────────────────────

export async function getHomepageData() {
  const res = await api.get('/items/public/homepage')
  return res.data
}

export async function browseItems({
  item_type = null,
  category = [],
  location_id = null,
  date_from = null,
  date_to = null,
  status = [],
  q = '',
  sort = 'newest',
  skip = 0,
  limit = 20,
} = {}) {
  const params = new URLSearchParams()
  if (item_type)   params.append('item_type', item_type)
  if (q)           params.append('q', q)
  if (sort)        params.append('sort', sort)
                   params.append('skip', String(skip))
                   params.append('limit', String(limit))
  if (location_id) params.append('location_id', location_id)
  if (date_from)   params.append('date_from', date_from)
  if (date_to)     params.append('date_to', date_to)
  category.forEach((c) => params.append('category', c))
  status.forEach((s)   => params.append('status', s))

  const res = await api.get(`/items/public?${params.toString()}`)
  return res.data
}

export async function getPublicCampusZones() {
  const res = await api.get('/items/public/campus-zones')
  return res.data
}
