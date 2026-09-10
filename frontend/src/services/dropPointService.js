/**
 * Drop point API (W2 — Section 4).
 */
import api from './api'

/**
 * List all drop points for a university.
 * @param {string} [universityId] — required when not logged in
 */
export async function listDropPoints(universityId) {
  const { data } = await api.get('/drop-points', {
    params: universityId ? { university_id: universityId } : undefined,
  })
  return data
}

/**
 * Nearest drop point + all alternatives sorted by distance.
 * @param {{ lat: number, lng: number, universityId?: string }} params
 */
export async function getNearestDropPoint({ lat, lng, universityId }) {
  const { data } = await api.get('/drop-points/nearest', {
    params: {
      lat,
      lng,
      ...(universityId ? { university_id: universityId } : {}),
    },
  })
  return data
}
