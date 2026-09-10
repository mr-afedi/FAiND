/**
 * Authority Claims tab — read-only list rows + detail panel with actions (Section 8.5).
 */
import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  getAuthorityClaimsList,
  getAuthorityClaimsForItem,
  callAuthorityClaimToCollect,
  verifyAuthorityClaim,
  rejectAuthorityClaim,
  replyToClaimInquiry,
} from '../services/authorityService'
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
import { invalidateAfterAuthorityClaimAction } from '../utils/queryCache'

export default function AuthorityClaimsTab({ highlightItemId = null }) {
  const queryClient = useQueryClient()
  const openLightbox = useAuthorityLightbox()
  const [selectedItemId, setSelectedItemId] = useState(null)
  const [selectedClaimId, setSelectedClaimId] = useState(null)
  const [actingId, setActingId] = useState(null)
  const [mobileSheetOpen, setMobileSheetOpen] = useState(false)
  const [presenceDialog, setPresenceDialog] = useState(null)
  const [itemPickerOpen, setItemPickerOpen] = useState(false)

  useEffect(() => {
    if (highlightItemId) setSelectedItemId(highlightItemId)
  }, [highlightItemId])

  const { data: listData, isLoading: listLoading } = useQuery({
    queryKey: ['authority-claims-list'],
    queryFn: getAuthorityClaimsList,
    refetchInterval: 30_000,
  })

  const items = listData?.items || []
  const activeItemId = selectedItemId || items[0]?.found_item_id || null

  const { data: comparison, isLoading: comparisonLoading } = useQuery({
    queryKey: ['authority-claims', activeItemId],
    queryFn: () => getAuthorityClaimsForItem(activeItemId),
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

  const afterAction = (data) => {
    queryClient.setQueryData(['authority-claims', activeItemId], data.comparison)
    invalidateAfterAuthorityClaimAction(queryClient, {
      foundItemId: activeItemId,
      claimId: selectedClaimId,
    })
  }

  const callMutation = useMutation({
    mutationFn: callAuthorityClaimToCollect,
    onMutate: (claimId) => setActingId(claimId),
    onSuccess: (data) => { afterAction(data); toast.success(data.message) },
    onError: (err) => toast.error(err.response?.data?.detail || 'Action failed'),
    onSettled: () => setActingId(null),
  })

  const verifyMutation = useMutation({
    mutationFn: verifyAuthorityClaim,
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
    mutationFn: rejectAuthorityClaim,
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
    mutationFn: ({ inquiryId, replyType }) => replyToClaimInquiry(inquiryId, replyType),
    onMutate: ({ inquiryId }) => setActingId(inquiryId),
    onSuccess: (data) => { afterAction(data); toast.success(data.message) },
    onError: (err) => toast.error(err.response?.data?.detail || 'Could not send reply'),
    onSettled: () => setActingId(null),
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
        <p className="text-base text-slate-400">No claims at this drop point yet.</p>
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
                    ? 'border-brand-500 bg-brand-900/20 text-brand-200'
                    : 'border-slate-700 text-slate-400 hover:border-slate-500'}`}
              >
                {item.found_item_description.slice(0, 48)}
                {item.pending_count > 0 && (
                  <span className="ml-2 text-amber-400">({item.pending_count} pending)</span>
                )}
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={() => setItemPickerOpen(true)}
            className="md:hidden w-full glass rounded-2xl border border-slate-800/80 p-4 text-left min-h-[48px]"
          >
            <p className="text-sm text-slate-500">Found item</p>
            <p className="text-base font-semibold text-slate-900 dark:text-slate-100 line-clamp-1 mt-0.5">
              {activeListItem?.found_item_description || 'Select item'}
            </p>
          </button>
        </>
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
              <ClaimantMobileCard
                key={claim.id}
                claim={claim}
                onSelect={openClaimSheet}
              />
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
                  ? 'border-brand-500 bg-brand-900/20'
                  : 'border-slate-800'}`}
            >
              <p className="text-base text-slate-900 dark:text-slate-100 line-clamp-2">{item.found_item_description}</p>
              {item.pending_count > 0 && (
                <p className="text-sm text-amber-400 mt-1">{item.pending_count} pending</p>
              )}
            </button>
          ))}
        </div>
      </StaffMobileBottomSheet>
    </div>
  )
}
