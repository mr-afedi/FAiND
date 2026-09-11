/**
 * Prompts users who skipped token escrow to claim pending tokens after login.
 */
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { useAuth } from '../context/AuthContext'
import { getEscrowStatus, claimEscrowMe } from '../services/tokenService'
import { getEscrowToken, clearEscrowToken } from '../utils/tokenEscrow'

export default function EscrowClaimPrompt() {
  const { isAuthenticated, authReady } = useAuth()
  const [pending, setPending] = useState(null)
  const [claiming, setClaiming] = useState(false)

  useEffect(() => {
    if (!authReady || !isAuthenticated) return
    const token = getEscrowToken()
    if (!token) return

    getEscrowStatus(token)
      .then((info) => {
        if (info.pending_total > 0) {
          setPending({ token, total: info.pending_total })
        } else {
          clearEscrowToken()
        }
      })
      .catch(() => {
        clearEscrowToken()
      })
  }, [authReady, isAuthenticated])

  if (!pending) return null

  async function handleClaim() {
    setClaiming(true)
    try {
      const data = await claimEscrowMe(pending.token)
      clearEscrowToken()
      setPending(null)
      toast.success(data.message)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not claim tokens')
    } finally {
      setClaiming(false)
    }
  }

  function handleDismiss() {
    clearEscrowToken()
    setPending(null)
  }

  return (
    <div className="fixed bottom-[calc(5rem+env(safe-area-inset-bottom))] md:bottom-[calc(1.5rem+env(safe-area-inset-bottom))]
                    left-4 right-4 md:left-auto md:right-6 md:max-w-sm z-50
                    glass p-4 border border-brand-300/60 dark:border-brand-700/50 shadow-lg">
      <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">
        Pending finder tokens
      </p>
      <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
        You have pending tokens from an item you found — claim them now?
        <strong className="text-slate-800 dark:text-slate-100"> ({pending.total} tokens)</strong>
      </p>
      <div className="flex gap-2 mt-3">
        <button
          type="button"
          className="btn-primary text-xs flex-1"
          disabled={claiming}
          onClick={handleClaim}
        >
          {claiming ? 'Claiming…' : 'Claim now'}
        </button>
        <button
          type="button"
          className="btn-secondary text-xs flex-1"
          disabled={claiming}
          onClick={handleDismiss}
        >
          Dismiss
        </button>
      </div>
    </div>
  )
}
