/**
 * Full-page auth layout — glassmorphism card centred on a gradient background.
 * Used by Login, Signup, VerifyEmail, ForgotPassword, and ResetPassword pages.
 */
export default function AuthLayout({ children }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4
                    bg-gradient-to-br from-slate-100 via-blue-50 to-indigo-100
                    dark:from-slate-950 dark:via-slate-900 dark:to-indigo-950">
      {/* Brand mark */}
      <div className="mb-8 text-center">
        <span className="text-3xl font-bold tracking-tight">
          <span className="text-slate-700 dark:text-slate-200">FA</span>
          <span className="text-brand-500">i</span>
          <span className="text-slate-700 dark:text-slate-200">ND</span>
        </span>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 tracking-wide uppercase">
          Lost &amp; Found — GCTU
        </p>
      </div>

      <div className="auth-card">{children}</div>

      <p className="mt-6 text-xs text-slate-400 dark:text-slate-600 text-center max-w-xs">
        Keep your conversation focused on recovering your item safely.
        Do not share passwords or sensitive personal information off-platform.
      </p>
    </div>
  )
}
