/**
 * Owner claim status — Section 13.1 / 13.2 structured inquiry.
 */
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import NavBar from '../components/NavBar'
import SubmitButton from '../components/SubmitButton'
import { useSubmitLock } from '../hooks/useSubmitLock'
import {
  getClaimStatus,
  sendClaimInquiry,
  INQUIRY_OPTIONS,
} from '../services/claimService'

function formatStatus(value) {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export default function ClaimStatusPage() {
  const { claimId } = useParams()
  const queryClient = useQueryClient()
  const { isSubmitting, tryAcquire, release } = useSubmitLock()
  const [messageType, setMessageType] = useState(INQUIRY_OPTIONS[0].value)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['claim-status', claimId],
    queryFn: () => getClaimStatus(claimId),
    refetchInterval: 30_000,
  })

  const inquiryMutation = useMutation({
    mutationFn: (type) => sendClaimInquiry(claimId, type),
    onSuccess: (result) => {
      toast.success(result.message)
      queryClient.invalidateQueries({ queryKey: ['claim-status', claimId] })
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Could not send inquiry'),
    onSettled: () => release(),
  })

  async function handleSendInquiry(e) {
    e.preventDefault()
    if (!tryAcquire()) return
    inquiryMutation.mutate(messageType)
  }

  if (isLoading) {
    return (
      <>
        <NavBar />
        <div className="page-container py-16 flex justify-center">
          <div className="w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
        </div>
      </>
    )
  }

  if (isError || !data) {
    return (
      <>
        <NavBar />
        <div className="page-container py-16 text-center text-slate-500">
          Could not load claim status.
        </div>
      </>
    )
  }

  const isReady = data.collection_phase === 'ready_for_collection'

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <NavBar />
      <div className="page-container py-8 max-w-lg">
        <Link
          to={`/items/${data.found_item_id}`}
          className="text-sm text-slate-500 hover:text-brand-600 dark:hover:text-brand-400 mb-4 inline-block"
        >
          ← Back to item
        </Link>

        <div className="glass p-6 space-y-5">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500">Claim status</p>
            <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100 mt-1">
              Check Status
            </h1>
          </div>

          <div className="rounded-xl border border-slate-200 dark:border-slate-700 p-4 space-y-2 text-sm">
            <p className="text-slate-800 dark:text-slate-200">{data.found_item_description}</p>
            <p className="text-slate-500">
              Item: <span className="text-slate-700 dark:text-slate-300">{formatStatus(data.found_item_status)}</span>
            </p>
            <p className="text-slate-500">
              Your claim: <span className="text-slate-700 dark:text-slate-300">{formatStatus(data.claim_status)}</span>
              <span className="ml-2 text-slate-400">(Path {data.claim_path})</span>
            </p>
            {isReady && data.drop_point_name && (
              <p className="text-emerald-700 dark:text-emerald-300">
                At {data.drop_point_name}
                {data.operating_hours ? ` · ${data.operating_hours}` : ''}
              </p>
            )}
            {!isReady && (
              <p className="text-amber-700 dark:text-amber-300 text-xs">
                This item has not arrived at the drop point yet. We will notify you when it is ready.
              </p>
            )}
          </div>

          {data.inquiry?.reply && (
            <div className="rounded-xl border border-brand-200 dark:border-brand-800 bg-brand-50/50 dark:bg-brand-950/30 p-4 space-y-2">
              <p className="text-xs uppercase tracking-wide text-slate-500">Authority reply</p>
              <p className="text-sm text-slate-800 dark:text-slate-200">{data.inquiry.reply.reply_label}</p>
              <p className="text-xs text-slate-400">
                {new Date(data.inquiry.reply.created_at).toLocaleString()}
              </p>
            </div>
          )}

          {data.inquiry && !data.inquiry.reply && (
            <div className="rounded-xl border border-slate-200 dark:border-slate-700 p-4 space-y-2">
              <p className="text-xs uppercase tracking-wide text-slate-500">Your inquiry</p>
              <p className="text-sm text-slate-800 dark:text-slate-200">{data.inquiry.message_label}</p>
              <p className="text-xs text-slate-400">Waiting for authority response…</p>
            </div>
          )}

          {data.can_send_inquiry && (
            <form onSubmit={handleSendInquiry} className="space-y-3 border-t border-slate-200/60 dark:border-slate-700/50 pt-4">
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Send one inquiry to staff
              </p>
              <p className="text-xs text-slate-500">
                Choose a predefined message — you can only send one per claim.
              </p>
              <select
                className="input-field w-full"
                value={messageType}
                onChange={(e) => setMessageType(e.target.value)}
              >
                {INQUIRY_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
              <SubmitButton type="submit" loading={isSubmitting} className="btn-primary text-sm w-full">
                Send inquiry
              </SubmitButton>
            </form>
          )}

          <div className="flex gap-3 pt-2">
            <Link to="/dashboard" className="btn-secondary text-sm">Dashboard</Link>
          </div>
        </div>
      </div>
    </div>
  )
}
