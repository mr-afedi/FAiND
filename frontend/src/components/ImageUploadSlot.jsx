/**
 * Shared image upload slot — skeleton + spinner while uploading;
 * shows image only after Cloudinary URL is confirmed.
 */
import { useRef } from 'react'
import { Camera, Plus, X } from './icons'
import { optimizeCloudinaryUrl } from '../utils/cloudinary'

export default function ImageUploadSlot({
  index = 0,
  imageUrl = null,
  uploading = false,
  required = false,
  onSelect,
  onRemove,
  className = 'w-28 h-28',
  emptyLabel,
  variant = 'light',
}) {
  const inputRef = useRef(null)
  const isDark = variant === 'dark'
  const borderIdle = isDark ? 'border-slate-600 hover:border-brand-400' : 'border-slate-300 dark:border-slate-600 hover:border-brand-400'
  const borderRequired = isDark
    ? 'border-red-700 bg-red-950/20'
    : 'border-red-400 dark:border-red-600 bg-red-50/50 dark:bg-red-900/10'
  const skeletonBg = isDark ? 'bg-slate-800' : 'bg-slate-200 dark:bg-slate-700'

  return (
    <div
      className={`relative ${className} rounded-xl border-2 border-dashed overflow-hidden
                  flex items-center justify-center transition-colors
                  ${required && !imageUrl && !uploading ? borderRequired : borderIdle}
                  ${!imageUrl && !uploading ? 'cursor-pointer' : ''}`}
      onClick={() => !imageUrl && !uploading && inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) onSelect?.(file)
          e.target.value = ''
        }}
      />

      {uploading ? (
        <div className={`absolute inset-0 ${skeletonBg} animate-pulse flex flex-col items-center justify-center gap-2`}>
          <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
          <span className={`text-[10px] ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Uploading…</span>
        </div>
      ) : imageUrl ? (
        <>
          <img
            src={optimizeCloudinaryUrl(imageUrl)}
            alt={index ? `Upload ${index + 1}` : 'Upload'}
            className="w-full h-full object-cover"
          />
          {onRemove && (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onRemove() }}
              className="absolute top-1 right-1 bg-red-600 text-white rounded-full w-5 h-5 flex items-center justify-center hover:bg-red-700"
              aria-label="Remove image"
            >
              <X className="w-3 h-3" aria-hidden />
            </button>
          )}
        </>
      ) : (
        <div className={`flex flex-col items-center gap-1 select-none ${isDark ? 'text-slate-500' : 'text-slate-400 dark:text-slate-500'}`}>
          {required ? <Camera className="w-7 h-7" aria-hidden /> : <Plus className="w-7 h-7" aria-hidden />}
          <span className="text-xs text-center leading-tight px-1">
            {emptyLabel || (required ? 'Required' : 'Add photo')}
          </span>
        </div>
      )}
    </div>
  )
}
