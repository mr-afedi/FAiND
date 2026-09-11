/**
 * Owner digital handover sign-off — Section 11.
 */
import { Link, useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import NavBar from '../components/NavBar'
import { getCategoryLabel } from '../components/icons'
import { getHandover, confirmHandover } from '../services/handoverService'
import { invalidateAfterHandover } from '../utils/queryCache'

export default function HandoverConfirmPage() {
  const { handoverId } = useParams()
  const queryClient = useQueryClient()

  const { data: handover, isLoading, isError, refetch } = useQuery({
    queryKey: ['handover', handoverId],
    queryFn: () => getHandover(handoverId),
  })

  const { mutate: confirm, isPending } = useMutation({
    mutationFn: () => confirmHandover(handoverId),
    onSuccess: (data) => {
      toast.success(data.message)
      invalidateAfterHandover(queryClient, {
        handoverId,
        foundItemId: data.found_item_id,
      })
      refetch()
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Could not confirm'),
  })

  if (isLoading) {
    return (
      <>
        <NavBar />
        <div className="page-container py-20 flex justify-center">
          <div className="w-9 h-9 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
        </div>
      </>
    )
  }

  if (isError || !handover) {
    return (
      <>
        <NavBar />
        <div className="page-container py-16 text-center">
          <p className="text-slate-500">Handover not found or access denied.</p>
          <Link to="/dashboard" className="btn-primary text-sm mt-4 inline-block">Dashboard</Link>
        </div>
      </>
    )
  }

  const complete = handover.owner_confirmed || handover.authority_override

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <NavBar />
      <div className="page-container py-8 max-w-lg mx-auto">
        <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100 mb-2">
          Confirm handover
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
          {getCategoryLabel(handover.found_item_category)} · {handover.found_item_description}
        </p>

        <div className="glass p-6 space-y-5">
          <div>
            <p className="text-xs text-slate-500 mb-2">Item condition at handover</p>
            <img
              src={handover.condition_photo_url}
              alt="Item condition at handover"
              className="w-full rounded-xl border border-slate-200 dark:border-slate-700 object-contain bg-slate-100 dark:bg-slate-900"
            />
          </div>

          {complete ? (
            <div className="rounded-xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50/80 dark:bg-emerald-900/20 p-4">
              <p className="text-sm font-semibold text-emerald-800 dark:text-emerald-200">
                {handover.authority_override
                  ? 'Handover completed by the drop point'
                  : 'You confirmed receipt'}
              </p>
              <p className="text-xs text-emerald-700 dark:text-emerald-300 mt-1">
                This item has been marked as returned.
              </p>
            </div>
          ) : (
            <>
              <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
                I confirm I received this item in the condition shown above.
              </p>
              <button
                type="button"
                onClick={() => confirm()}
                disabled={isPending || !handover.can_confirm}
                className="btn-primary w-full"
              >
                {isPending ? 'Confirming…' : 'I Confirm'}
              </button>
            </>
          )}
        </div>

        <p className="text-center mt-6">
          <Link to="/dashboard" className="text-sm text-slate-500 hover:text-brand-600">
            Back to dashboard
          </Link>
        </p>
      </div>
    </div>
  )
}
