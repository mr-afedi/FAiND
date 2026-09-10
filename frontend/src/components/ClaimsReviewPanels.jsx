/**
 * Shared claims review UI — authority (actions) and supervisor (read-only detail).
 */
import { useState } from 'react'
import toast from 'react-hot-toast'
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  PhoneCall,
  XCircle,
  ImageIcon,
} from 'lucide-react'
import { getCategoryLabel } from './icons'
import CloudinaryImage from './CloudinaryImage'
import PhysicalPresenceDialog, {
  PHYSICAL_PRESENCE_REJECT_WARNING,
  PHYSICAL_PRESENCE_WARNING,
} from './PhysicalPresenceDialog'
import { REPLY_OPTIONS, replyLabel } from '../services/claimService'
import { formatClaimWhen, claimStatusBadge } from './claimsReviewUtils'

export { formatClaimWhen, claimStatusBadge } from './claimsReviewUtils'

function StatusIcon({ status }) {
  if (status === 'verified') return <CheckCircle className="w-4 h-4 text-emerald-400" aria-hidden />
  if (status === 'rejected') return <XCircle className="w-4 h-4 text-slate-400" aria-hidden />
  return <Clock className="w-4 h-4 text-amber-400" aria-hidden />
}

function LightboxThumb({ src, images, index, onOpen, className }) {
  if (!src) return null
  return (
    <button
      type="button"
      onClick={() => onOpen?.(images, index)}
      className={`block overflow-hidden ${className}`}
    >
      <CloudinaryImage src={src} alt="" className="w-full h-full object-cover" />
    </button>
  )
}

export function ClaimantMobileCard({ claim, onSelect }) {
  return (
    <button
      type="button"
      onClick={() => onSelect(claim.id)}
      className="md:hidden w-full text-left glass rounded-2xl border border-slate-800/80 p-4
                 space-y-3 active:bg-slate-900/50 min-h-[44px]"
    >
      <div className="flex items-start gap-3">
        {claim.photo_url ? (
          <div className="w-14 h-14 rounded-xl overflow-hidden border border-slate-700 shrink-0">
            <CloudinaryImage src={claim.photo_url} alt="" className="w-full h-full object-cover" />
          </div>
        ) : (
          <div className="w-14 h-14 rounded-xl bg-slate-800 flex items-center justify-center shrink-0">
            <ImageIcon className="w-6 h-6 text-slate-500" aria-hidden />
          </div>
        )}
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <p className="text-base font-semibold text-slate-900 dark:text-slate-100 truncate">{claim.claimant_name}</p>
            <span className={`inline-flex items-center gap-1 text-xs font-bold uppercase px-2 py-0.5 rounded-full shrink-0 ${claimStatusBadge(claim.status)}`}>
              <StatusIcon status={claim.status} />
              {claim.status}
            </span>
          </div>
          <p className="text-sm text-slate-500 truncate">{claim.claimant_email}</p>
          <p className="text-sm text-slate-400 mt-1">{formatClaimWhen(claim.created_at)}</p>
        </div>
      </div>
      <p className="text-base text-slate-700 dark:text-slate-300 line-clamp-2 leading-relaxed">{claim.description}</p>
    </button>
  )
}

export function ClaimantListRow({ claim, selected, onSelect }) {
  return (
    <button
      type="button"
      onClick={() => onSelect(claim.id)}
      className={`hidden md:block w-full text-left glass px-4 py-3 border transition-colors
        ${selected
          ? 'border-brand-500 bg-brand-900/20'
          : 'border-slate-800/80 hover:border-slate-600'}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-slate-900 dark:text-slate-100 truncate">{claim.claimant_name}</p>
          <p className="text-xs text-slate-500 truncate">{claim.claimant_email}</p>
        </div>
        <span className={`text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full shrink-0 ${claimStatusBadge(claim.status)}`}>
          {claim.status}
        </span>
      </div>
      <p className="text-xs text-slate-400 mt-1.5 line-clamp-2">{claim.description}</p>
      <p className="text-[10px] text-slate-600 mt-1">
        Path {claim.claim_path} · {formatClaimWhen(claim.created_at)}
      </p>
    </button>
  )
}

export function ClaimantDetailBody({
  claim,
  operatingHours,
  onAction,
  actingId,
  onImageOpen,
  showActions = true,
  showInquiryReplies = true,
}) {
  if (!claim) return null

  const inquiry = claim.inquiry
  const pendingInquiry = inquiry && !inquiry.reply

  return (
    <div className="flex flex-col gap-4 text-base leading-relaxed">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-lg font-semibold text-slate-900 dark:text-slate-100">{claim.claimant_name}</p>
          <p className="text-sm text-slate-500">{claim.claimant_email}</p>
        </div>
        <span className={`inline-flex items-center gap-1 text-xs font-bold uppercase px-2 py-1 rounded-full ${claimStatusBadge(claim.status)}`}>
          <StatusIcon status={claim.status} />
          {claim.status}
        </span>
      </div>

      <div className="text-sm text-slate-400 space-y-1">
        <p>
          Path {claim.claim_path}
          {claim.claim_path === 'A' && claim.ai_confidence_score != null && (
            <span className="ml-2 text-violet-300">
              AI {Math.round(claim.ai_confidence_score * 100)}%
            </span>
          )}
        </p>
        {claim.student_id && (
          <p>Student ID: <span className="text-slate-700 dark:text-slate-300 font-mono">{claim.student_id}</span></p>
        )}
        {claim.date_lost && claim.time_lost && (
          <p>Lost: {claim.date_lost} at {claim.time_lost}</p>
        )}
        {claim.lost_location && (
          <p>Location: <span className="text-slate-700 dark:text-slate-300">{claim.lost_location}</span></p>
        )}
        <p>Submitted: {formatClaimWhen(claim.created_at)}</p>
      </div>

      {claim.photo_url && (
        <LightboxThumb
          src={claim.photo_url}
          images={[claim.photo_url]}
          index={0}
          onOpen={onImageOpen}
          className="w-full max-h-56 rounded-xl border border-slate-700"
        />
      )}

      <p className="text-base text-slate-700 dark:text-slate-300">{claim.description}</p>

      {inquiry && (
        <div className={`rounded-xl p-4 text-sm space-y-2 ${
          pendingInquiry
            ? 'border border-amber-700/50 bg-amber-950/30'
            : 'border border-slate-700 bg-slate-900/40'
        }`}>
          <p className="font-semibold text-slate-800 dark:text-slate-200">
            {pendingInquiry ? 'Owner inquiry' : 'Inquiry'}
          </p>
          <p className="text-slate-700 dark:text-slate-300">{inquiry.message_label}</p>
          {inquiry.reply && (
            <p className="text-emerald-300">Replied: {inquiry.reply.reply_label}</p>
          )}
          {pendingInquiry && showActions && showInquiryReplies && (
            <div className="flex flex-col gap-2 pt-1">
              {REPLY_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  disabled={Boolean(actingId)}
                  onClick={() => onAction?.('reply', inquiry.id, opt.value)}
                  className="text-left text-sm py-3 px-4 rounded-xl border border-slate-600
                             text-slate-800 dark:text-slate-200 hover:bg-slate-800 disabled:opacity-50 min-h-[48px]"
                >
                  {replyLabel(opt, operatingHours)}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export function ClaimantActionFooter({
  claim,
  onAction,
  actingId,
  showActions = true,
  onVerifyClick,
  onRejectClick,
  mobile = false,
}) {
  if (!claim || claim.status !== 'pending' || !showActions) {
    if (claim?.status === 'pending' && !showActions) {
      return (
        <p className="text-sm text-slate-500">
          Verification actions are performed by the drop point authority in person.
        </p>
      )
    }
    return null
  }

  const busy = actingId === claim.id
  const warningClass = mobile
    ? 'flex items-start gap-2 text-sm text-amber-200 bg-amber-950/50 border border-amber-700/50 rounded-xl px-4 py-3 leading-relaxed'
    : 'text-[11px] text-amber-300/90 bg-amber-950/30 border border-amber-800/40 rounded-lg px-3 py-2 leading-snug'

  return (
    <div className="flex flex-col gap-3">
      <button
        type="button"
        disabled={Boolean(actingId)}
        onClick={() => onAction?.('call', claim.id)}
        className="btn-secondary w-full min-h-[48px] text-base inline-flex items-center justify-center gap-2"
      >
        <PhoneCall className="w-5 h-5" aria-hidden />
        {busy ? 'Sending…' : 'Call to Collect'}
      </button>

      <div className={warningClass}>
        <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" strokeWidth={1.75} aria-hidden />
        <span>{PHYSICAL_PRESENCE_WARNING}</span>
      </div>
      <button
        type="button"
        disabled={Boolean(actingId)}
        onClick={onVerifyClick}
        className="btn-primary w-full min-h-[48px] text-base"
      >
        {busy ? 'Verifying…' : 'Verify as Owner'}
      </button>

      <div className={warningClass}>
        <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" strokeWidth={1.75} aria-hidden />
        <span>{PHYSICAL_PRESENCE_REJECT_WARNING}</span>
      </div>
      <button
        type="button"
        disabled={Boolean(actingId)}
        onClick={onRejectClick}
        className="w-full min-h-[48px] text-base rounded-xl border border-red-800 text-red-400
                   hover:bg-red-900/20 disabled:opacity-50"
      >
        {busy ? 'Rejecting…' : 'Reject'}
      </button>
    </div>
  )
}

export function ClaimantDetailPanel({
  claim,
  operatingHours,
  onAction,
  actingId,
  onImageOpen,
  showActions = true,
}) {
  const [dialog, setDialog] = useState(null)

  if (!claim) {
    return (
      <div className="hidden md:block glass p-8 text-center border border-slate-800/80">
        <p className="text-sm text-slate-500">Select a claimant to review full details.</p>
      </div>
    )
  }

  function handleWait(kind) {
    setDialog(null)
    const msg = kind === 'reject'
      ? 'Please wait until the claimant arrives in person before rejecting.'
      : 'Please wait until the claimant arrives in person before verifying.'
    toast(msg)
  }

  function handleVerifyConfirm() {
    setDialog(null)
    onAction?.('verify', claim.id)
  }

  function handleRejectConfirm() {
    setDialog(null)
    onAction?.('reject', claim.id)
  }

  return (
    <>
      <article className="hidden md:flex glass p-5 flex-col gap-4 border border-slate-800/80">
        <ClaimantDetailBody
          claim={claim}
          operatingHours={operatingHours}
          onAction={onAction}
          actingId={actingId}
          onImageOpen={onImageOpen}
          showActions={showActions}
        />
        <ClaimantActionFooter
          claim={claim}
          onAction={onAction}
          actingId={actingId}
          showActions={showActions}
          onVerifyClick={() => setDialog('verify')}
          onRejectClick={() => setDialog('reject')}
        />
      </article>

      <PhysicalPresenceDialog
        open={dialog === 'verify'}
        kind="verify"
        onConfirm={handleVerifyConfirm}
        onWait={() => handleWait('verify')}
      />
      <PhysicalPresenceDialog
        open={dialog === 'reject'}
        kind="reject"
        onConfirm={handleRejectConfirm}
        onWait={() => handleWait('reject')}
      />
    </>
  )
}


export function ClaimsItemHeader({ comparison, onImageOpen, onTap }) {
  if (!comparison) return null
  const inner = (
    <>
      <p className="text-sm text-slate-500 uppercase tracking-wide">
        {getCategoryLabel(comparison.found_item_category)}
        <span className="ml-2 text-slate-400">{comparison.found_item_status}</span>
      </p>
      <p className="text-base md:text-sm font-semibold text-slate-900 dark:text-slate-100 mt-1 leading-snug">
        {comparison.found_item_description}
      </p>
      {comparison.found_item_image_urls?.length > 0 && (
        <div className="flex gap-2 mt-3 flex-wrap">
          {comparison.found_item_image_urls.map((url, i) => (
            <LightboxThumb
              key={url}
              src={url}
              images={comparison.found_item_image_urls}
              index={i}
              onOpen={onImageOpen}
              className="w-16 h-16 md:w-14 md:h-14 rounded-lg border border-slate-700"
            />
          ))}
        </div>
      )}
    </>
  )

  if (onTap) {
    return (
      <button
        type="button"
        onClick={onTap}
        className="md:hidden w-full text-left glass rounded-2xl p-4 border border-slate-800/80"
      >
        {inner}
      </button>
    )
  }

  return (
    <div className="hidden md:block glass p-4 border border-slate-800/80">
      {inner}
    </div>
  )
}
