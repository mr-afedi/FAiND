/**
 * Cloudinary delivery URL helpers — f_auto,q_auto for optimized images.
 */

export function isCloudinaryUrl(url) {
  return Boolean(url && typeof url === 'string' && url.includes('res.cloudinary.com'))
}

/** Append f_auto,q_auto transformation for faster delivery. */
export function optimizeCloudinaryUrl(url) {
  if (!url || !isCloudinaryUrl(url)) return url
  if (url.includes('/f_auto,q_auto/')) return url
  return url.replace('/upload/', '/upload/f_auto,q_auto/')
}
