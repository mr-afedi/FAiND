/** localStorage helpers for anonymous found-item tracking (Section 7.3). */
const STORAGE_KEY = 'faind_found_tracking_refs'

function normalizeEntry(entry) {
  if (!entry) return null
  if (typeof entry === 'string') {
    return { ref: entry, itemId: null, dropPointName: null }
  }
  if (typeof entry === 'object' && entry.ref) {
    return {
      ref: entry.ref,
      itemId: entry.itemId || null,
      dropPointName: entry.dropPointName || null,
    }
  }
  return null
}

function readEntries() {
  try {
    const list = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
    if (!Array.isArray(list)) return []
    return list.map(normalizeEntry).filter(Boolean)
  } catch {
    return []
  }
}

function writeEntries(entries) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entries.slice(0, 20)))
  } catch {
    /* ignore quota / private mode */
  }
}

export function saveFoundTrackingRef(ref, itemId = null, dropPointName = null) {
  if (!ref) return
  const code = String(ref).trim().toUpperCase()
  const existing = readEntries().filter((e) => e.ref !== code)
  const next = [
    {
      ref: code,
      itemId: itemId || null,
      dropPointName: dropPointName || null,
    },
    ...existing,
  ].slice(0, 20)
  writeEntries(next)
}

export function getSavedTrackingRefs() {
  return readEntries().map((e) => e.ref)
}

export function getLatestTrackingRef() {
  return readEntries()[0]?.ref || ''
}

export function getTrackingRefForItem(itemId) {
  if (!itemId) return ''
  const id = String(itemId)
  const hit = readEntries().find((e) => e.itemId && String(e.itemId) === id)
  return hit?.ref || ''
}

export function getDropPointNameForItem(itemId) {
  if (!itemId) return null
  const id = String(itemId)
  const hit = readEntries().find((e) => e.itemId && String(e.itemId) === id)
  return hit?.dropPointName || null
}

export function isFinderForItem(item, userId = null) {
  if (!item || item.item_type !== 'found') return false
  if (userId && item.posted_by?.id === userId) return true
  const id = String(item.id)
  return readEntries().some((e) => e.itemId && String(e.itemId) === id)
}

export function shouldShowFinderTrack(item) {
  if (!item) return false
  const terminal = ['at_droppoint', 'under_claim_review', 'returned', 'archived', 'unconfirmed']
  return !terminal.includes(item.status)
}

export function getItemDetailPath(itemId) {
  return `/items/${itemId}`
}
