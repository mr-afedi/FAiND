/**
 * Supervisor Claims tab — full authority-style review with dispute resolution (Section 15.2).
 */
import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  getSupervisorClaimsList,
  getSupervisorClaimsForItem,
  callSupervisorClaimToCollect,
  verifySupervisorClaim,
  rejectSupervisorClaim,
  replyToSupervisorInquiry,
  escalateSupervisorDispute,
} from '../services/supervisorService'
import { useAuthorityLightbox } from '../context/AuthorityLightboxContext'
import {
  ClaimantDetailPanel,
  ClaimantListRow,
  ClaimantMobileCard,
  ClaimantDetailBody,
  ClaimantActionFooter,
  ClaimsItemHeader,
} from './ClaimsReviewPanels'
import PhysicalPresenceDialog from './PhysicalPresenceDialog'
import StaffMobileBottomSheet from './staff-mobile/StaffMobileBottomSheet'

export default function SupervisorClaimsTab({ filterDp = '', highlightItemId = null }) {
  const queryClient = useQueryClient()
  const openLightbox = useAuthorityLightbox()
  const [selectedItemId, setSelectedItemId] = useState(null)
  const [selectedClaimId, setSelectedClaimId] = useState(null)
  const [actingId, setActingId] = useState(null)
  const [mobileSheetOpen, setMobileSheetOpen] = useState(false)
  const [presenceDialog, setPresenceDialog] = useState(null)
  const [itemPickerOpen, setItemPickerOpen] = useState(false)
  const [escalateOpen, setEscalateOpen] = useState(false)
  const [escalateNote, setEscalateNote] = useState('')

  useEffect(() => {
    if (highlightItemId) setSelectedItemId(highlightItemId)
  }, [highlightItemId])

  const { data: listData, isLoading: listLoading } = useQuery({
    queryKey: ['supervisor-claims-list', filterDp],
    queryFn: () => getSupervisorClaimsList(filterDp || undefined),
    refetchInterval: 30_000,
  })

  const items = listData?.items || []
  const activeItemId = selectedItemId || items[0]?.found_item_id || null

  const { data: comparison, isLoading: comparisonLoading } = useQuery({
    queryKey: ['supervisor-claims', activeItemId],
    queryFn: () => getSupervisorClaimsForItem(activeItemId),
    enabled: Boolean(activeItemId),
    refetchInterval: 30_000,
  })

  useEffect(() => {
    if (!comparison?.claims?.length) {
      setSelectedClaimId(null)
      setMobileSheetOpen(false)
      return
    }
    if (!selectedClaimId || !comparison.claims.some((c) => c.id === selectedClaimId)) {
      setSelectedClaimId(comparison.claims[0].id)
    }
  }, [comparison, selectedClaimId])

  const selectedClaim = comparison?.claims?.find((c) => c.id === selectedClaimId) || null
  const activeListItem = items.find((i) => i.found_item_id === activeItemId)

  const invalidateClaims = () => {
    queryClient.invalidateQueries({ queryKey: ['supervisor-claims-list'] })
    queryClient.invalidateQueries({ queryKey: ['supervisor-claims', activeItemId] })
    queryClient.invalidateQueries({ queryKey: ['supervisor-overview'] })
    queryClient.invalidateQueries({ queryKey: ['supervisor-handover'] })
  }

  const afterAction = (data) => {
    queryClient.setQueryData(['supervisor-claims', activeItemId], data.comparison)
    invalidateClaims()
  }

  const callMutation = useMutation({
    mutationFn: callSupervisorClaimToCollect,
    onMutate: (claimId) => setActingId(claimId),
    onSuccess: (data) => { afterAction(data); toast.success(data.message) },
    onError: (err) => toast.error(err.response?.data?.detail || 'Action failed'),
    onSettled: () => setActingId(null),
  })

  const verifyMutation = useMutation({
    mutationFn: verifySupervisorClaim,
    onMutate: (claimId) => setActingId(claimId),
    onSuccess: (data) => {
      afterAction(data)
      toast.success(data.message)
      setMobileSheetOpen(false)
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Could not verify'),
    onSettled: () => setActingId(null),
  })

  const rejectMutation = useMutation({
    mutationFn: rejectSupervisorClaim,
    onMutate: (claimId) => setActingId(claimId),
    onSuccess: (data) => {
      afterAction(data)
      toast.success(data.message)
      setMobileSheetOpen(false)
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Could not reject'),
    onSettled: () => setActingId(null),
  })

  const replyMutation = useMutation({
    mutationFn: ({ inquiryId, replyType }) => replyToSupervisorInquiry(inquiryId, replyType),
    onMutate: ({ inquiryId }) => setActingId(inquiryId),
    onSuccess: (data) => { afterAction(data); toast.success(data.message) },
    onError: (err) => toast.error(err.response?.data?.detail || 'Could not send reply'),
    onSettled: () => setActingId(null),
  })

  const escalateMutation = useMutation({
    mutationFn: ({ foundItemId, note }) => escalateSupervisorDispute(foundItemId, note),
    onSuccess: (data) => {
      toast.success(data.message)
      setEscalateOpen(false)
      setEscalateNote('')
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Could not escalate'),
  })

  function handleAction(action, id, replyType) {
    if (action === 'call') callMutation.mutate(id)
    else if (action === 'verify') verifyMutation.mutate(id)
    else if (action === 'reject') rejectMutation.mutate(id)
    else if (action === 'reply') replyMutation.mutate({ inquiryId: id, replyType })
  }

  function openClaimSheet(claimId) {
    setSelectedClaimId(claimId)
    setMobileSheetOpen(true)
  }

  if (listLoading) {
    return (
      <div className="flex justify-center py-16">
        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="glass p-8 text-center rounded-2xl">
        <p className="text-base text-slate-500 dark:text-slate-400">No claims in your assigned drop points.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {items.length > 1 && (
        <>
          <div className="hidden md:flex gap-2 overflow-x-auto pb-1">
            {items.map((item) => (
              <button
                key={item.found_item_id}
                type="button"
                onClick={() => {
                  setSelectedItemId(item.found_item_id)
                  setSelectedClaimId(null)
                }}
                className={`text-left text-xs rounded-lg px-3 py-2 border whitespace-nowrap max-w-xs truncate
                  ${activeItemId === item.found_item_id
                    ? 'border-brand-500 bg-brand-100 dark:bg-brand-900/20 text-brand-700 dark:text-brand-200'
                    : 'border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:border-slate-400'}
                  ${item.has_dispute ? 'ring-1 ring-amber-500/60' : ''}`}
              >
                {item.found_item_description.slice(0, 48)}
                {item.has_dispute && <span className="ml-2 text-amber-600 dark:text-amber-400">Dispute</span>}
                {!item.has_dispute && item.pending_count > 0 && (
                  <span className="ml-2 text-amber-600 dark:text-amber-400">({item.pending_count} pending)</span>
                )}
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={() => setItemPickerOpen(true)}
            className="md:hidden w-full glass rounded-2xl border border-slate-200 dark:border-slate-800/80 p-4 text-left min-h-[48px]"
          >
            <p className="text-sm text-slate-500">Found item</p>
            <p className="text-base font-semibold text-slate-900 dark:text-slate-100 line-clamp-1 mt-0.5">
              {activeListItem?.found_item_description || 'Select item'}
              {activeListItem?.has_dispute && (
                <span className="ml-2 text-amber-600 dark:text-amber-400 text-sm">· Dispute</span>
              )}
            </p>
          </button>
        </>
      )}

      {activeListItem?.has_dispute && (
        <div className="rounded-2xl border border-amber-500/50 bg-amber-50 dark:bg-amber-900/20 p-4 space-y-3">
          <p className="text-sm font-semibold text-amber-800 dark:text-amber-200">
            Dispute flagged — multiple competing claims on this item
          </p>
          <p className="text-xs text-amber-700/80 dark:text-amber-300/80">
            Verify the correct claimant in person to assign the item and start handover, or escalate to Root Admin.
          </p>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setEscalateOpen(true)}
              className="btn-secondary text-sm min-h-[44px]"
            >
              Escalate to Root Admin
            </button>
          </div>
        </div>
      )}

      {comparisonLoading && (
        <div className="flex justify-center py-12">
          <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {!comparisonLoading && comparison && (
        <div className="space-y-4">
          <ClaimsItemHeader comparison={comparison} onImageOpen={openLightbox} />

          <div className="md:hidden space-y-3">
            <p className="text-sm font-semibold text-slate-500 uppercase tracking-wide px-1">
              Claimants ({comparison.claims.length})
            </p>
            {comparison.claims.map((claim) => (
              <ClaimantMobileCard key={claim.id} claim={claim} onSelect={openClaimSheet} />
            ))}
          </div>

          <div className="hidden md:grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)] gap-4">
            <div className="space-y-2">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide px-1">
                Claimants
              </p>
              {comparison.claims.map((claim) => (
                <ClaimantListRow
                  key={claim.id}
                  claim={claim}
                  selected={claim.id === selectedClaimId}
                  onSelect={setSelectedClaimId}
                />
              ))}
            </div>

            <ClaimantDetailPanel
              claim={selectedClaim}
              operatingHours={comparison.drop_point_operating_hours}
              onAction={handleAction}
              actingId={actingId}
              onImageOpen={openLightbox}
              showActions
            />
          </div>
        </div>
      )}

      <StaffMobileBottomSheet
        open={mobileSheetOpen && Boolean(selectedClaim)}
        onClose={() => setMobileSheetOpen(false)}
        title={selectedClaim?.claimant_name}
        footer={selectedClaim && (
          <ClaimantActionFooter
            claim={selectedClaim}
            onAction={handleAction}
            actingId={actingId}
            showActions
            mobile
            onVerifyClick={() => setPresenceDialog('verify')}
            onRejectClick={() => setPresenceDialog('reject')}
          />
        )}
      >
        {selectedClaim && (
          <ClaimantDetailBody
            claim={selectedClaim}
            operatingHours={comparison?.drop_point_operating_hours}
            onAction={handleAction}
            actingId={actingId}
            onImageOpen={openLightbox}
            showActions
            showInquiryReplies
          />
        )}
      </StaffMobileBottomSheet>

      <PhysicalPresenceDialog
        open={presenceDialog === 'verify'}
        kind="verify"
        onConfirm={() => {
          setPresenceDialog(null)
          if (selectedClaim) handleAction('verify', selectedClaim.id)
        }}
        onWait={() => {
          setPresenceDialog(null)
          toast('Please wait until the claimant arrives in person before verifying.')
        }}
      />
      <PhysicalPresenceDialog
        open={presenceDialog === 'reject'}
        kind="reject"
        onConfirm={() => {
          setPresenceDialog(null)
          if (selectedClaim) handleAction('reject', selectedClaim.id)
        }}
        onWait={() => {
          setPresenceDialog(null)
          toast('Please wait until the claimant arrives in person before rejecting.')
        }}
      />

      <StaffMobileBottomSheet
        open={itemPickerOpen}
        onClose={() => setItemPickerOpen(false)}
        title="Select found item"
      >
        <div className="space-y-2">
          {items.map((item) => (
            <button
              key={item.found_item_id}
              type="button"
              onClick={() => {
                setSelectedItemId(item.found_item_id)
                setSelectedClaimId(null)
                setItemPickerOpen(false)
              }}
              className={`w-full text-left p-4 rounded-xl border min-h-[48px]
                ${activeItemId === item.found_item_id
                  ? 'border-brand-500 bg-brand-100 dark:bg-brand-900/20'
                  : 'border-slate-200 dark:border-slate-800'}
                ${item.has_dispute ? 'ring-1 ring-amber-500/50' : ''}`}
            >
              <p className="text-base text-slate-900 dark:text-slate-100 line-clamp-2">
                {item.found_item_description}
              </p>
              {item.has_dispute && (
                <p className="text-sm text-amber-600 dark:text-amber-400 mt-1">Dispute</p>
              )}
            </button>
          ))}
        </div>
      </StaffMobileBottomSheet>

      <StaffMobileBottomSheet
        open={escalateOpen}
        onClose={() => setEscalateOpen(false)}
        title="Escalate to Root Admin"
      >
        <div className="space-y-3">
          <textarea
            className="input-field w-full min-h-[100px]"
            placeholder="Explain why this dispute needs admin review (min 10 characters)"
            value={escalateNote}
            onChange={(e) => setEscalateNote(e.target.value)}
          />
          <button
            type="button"
            className="btn-primary w-full min-h-[48px]"
            disabled={escalateNote.trim().length < 10 || escalateMutation.isPending}
            onClick={() => escalateMutation.mutate({ foundItemId: activeItemId, note: escalateNote.trim() })}
          >
            Submit escalation
          </button>
        </div>
      </StaffMobileBottomSheet>
    </div>
  )
}
