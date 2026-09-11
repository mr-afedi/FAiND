/**
 * Primary form submit control — disabled + spinner while loading.
 */
export default function SubmitButton({
  loading = false,
  disabled = false,
  children,
  loadingLabel = 'Submitting…',
  className = 'btn-primary',
  ...props
}) {
  return (
    <button
      type="submit"
      disabled={loading || disabled}
      className={className}
      {...props}
    >
      {loading ? (
        <span className="flex items-center justify-center gap-2">
          <span
            className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin"
            aria-hidden
          />
          {loadingLabel}
        </span>
      ) : (
        children
      )}
    </button>
  )
}
