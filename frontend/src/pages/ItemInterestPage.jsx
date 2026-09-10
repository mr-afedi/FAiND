/**
 * Item interest — "Notify Me When Dropped Off" (V5).
 */
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import NavBar from '../components/NavBar'
import SubmitButton from '../components/SubmitButton'
import { useSubmitLock } from '../hooks/useSubmitLock'
import { getItemDetail, getItemInterestStatus, registerItemInterest } from '../services/itemService'
import { getCategoryLabel, ChevronLeft } from '../components/icons'

export default function ItemInterestPage() {
  const { itemId } = useParams()
  const navigate = useNavigate()
  const { isSubmitting, tryAcquire, release } = useSubmitLock()
  const [registered, setRegistered] = useState(false)

  const { data: item, isLoading: itemLoading } = useQuery({
    queryKey: ['item', itemId],
    queryFn: () => getItemDetail(itemId),
    enabled: Boolean(itemId),
  })

  const { data: interest, isLoading: interestLoading } = useQuery({
    queryKey: ['item-interest', itemId],
    queryFn: () => getItemInterestStatus(itemId),
    enabled: Boolean(itemId),
  })

  const registerMutation = useMutation({
    mutationFn: () => registerItemInterest(itemId),
    onSuccess: (result) => {
      setRegistered(true)
      toast.success(result.message)
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Could not register interest'),
    onSettled: () => release(),
  })

  const isLoading = itemLoading || interestLoading
  const dropPointName = interest?.drop_point_name || 'the drop point'
  const alreadyRegistered = registered || interest?.registered

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
        <NavBar />
        <div className="flex justify-center py-24">
          <div className="w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    )
  }

  if (!item || !interest) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
        <NavBar />
        <div className="max-w-lg mx-auto px-4 py-16 text-center">
          <p className="text-slate-500">Item not found.</p>
          <Link to="/found" className="btn-primary text-sm mt-4 inline-block">Browse found items</Link>
        </div>
      </div>
    )
  }

  if (interest.can_claim_now) {
    navigate(`/claims/found/${itemId}?path=c`, { replace: true })
    return null
  }

  if (!interest.requires_interest_flow) {
    navigate(`/items/${itemId}`, { replace: true })
    return null
  }

  function handleRegister() {
    if (!tryAcquire()) return
    registerMutation.mutate()
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <NavBar />
      <div className="max-w-lg mx-auto px-4 py-6">
        <button
          type="button"
          onClick={() => navigate(`/items/${itemId}`)}
          className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-brand-600 mb-4"
        >
          <ChevronLeft className="w-4 h-4" aria-hidden />
          Back to item
        </button>

        <div className="glass p-6 space-y-5">
          <div className="flex gap-3">
            {item.image_urls?.[0] ? (
              <img src={item.image_urls[0]} alt="" className="w-16 h-16 rounded-xl object-cover" />
            ) : (
              <div className="w-16 h-16 rounded-xl bg-slate-100 dark:bg-slate-800" />
            )}
            <div>
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                {getCategoryLabel(item.category)}
              </p>
              <p className="text-xs text-slate-500 line-clamp-2 mt-0.5">{item.public_description}</p>
            </div>
          </div>

          {alreadyRegistered ? (
            <div className="rounded-xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50/80 dark:bg-emerald-900/20 p-4 space-y-2">
              <p className="text-sm font-semibold text-emerald-800 dark:text-emerald-200">
                You&apos;re on the list
              </p>
              <p className="text-sm text-emerald-700 dark:text-emerald-300">
                We will notify you the moment this item arrives at {dropPointName} so you can submit your claim.
              </p>
              {interest.operating_hours && (
                <p className="text-xs text-emerald-600 dark:text-emerald-400">
                  Drop point hours: {interest.operating_hours}
                </p>
              )}
            </div>
          ) : (
            <>
              <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                This item has not been dropped off yet. We will notify you the moment it arrives at{' '}
                <span className="font-medium text-slate-800 dark:text-slate-200">{dropPointName}</span>{' '}
                so you can submit your claim.
              </p>
              {interest.operating_hours && (
                <p className="text-xs text-slate-500">Operating hours: {interest.operating_hours}</p>
              )}
              <SubmitButton
                type="button"
                onClick={handleRegister}
                loading={isSubmitting || registerMutation.isPending}
                className="btn-primary w-full"
              >
                Notify Me When Dropped Off
              </SubmitButton>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
