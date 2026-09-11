/**
 * Non-submit action button — disabled + spinner while an async action runs.
 */
export default function LoadingButton({
  loading = false,
  disabled = false,
  children,
  loadingLabel = 'Please wait…',
  className = 'btn-primary',
  type = 'button',
  ...props
}) {
  return (
    <button
      type={type}
      disabled={loading || disabled}
      className={className}
      {...props}
    >
      {loading ? (
        <span className="flex items-center justify-center gap-2">
          <span
            className="w-4 h-4 border-2 border-current/30 border-t-current rounded-full animate-spin"
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
