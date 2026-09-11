import { optimizeCloudinaryUrl } from '../utils/cloudinary'

/** img wrapper that applies Cloudinary f_auto,q_auto when applicable. */
export default function CloudinaryImage({ src, alt = '', className = '', ...props }) {
  if (!src) return null
  return (
    <img
      src={optimizeCloudinaryUrl(src)}
      alt={alt}
      className={className}
      {...props}
    />
  )
}
