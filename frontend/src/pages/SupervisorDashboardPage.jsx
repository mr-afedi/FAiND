/**
 * Supervisor dashboard — Section 15.2 (scoped drop points, all tabs).
 */
import { useState, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useSupervisorAuth } from '../context/SupervisorAuthContext'
import {
  getSupervisorOverview,
  getSupervisorIncoming,
  getSupervisorAtDroppoint,
  getSupervisorClaimsList,
  listSupervisorAuthorities,
  createSupervisorAuthority,
  deactivateSupervisorAuthority,
  activateSupervisorAuthority,
  resetSupervisorAuthorityPassword,
  supervisorLookupRedemptionCode,
} from '../services/supervisorService'
import StaffPushSettingsToggle from '../components/StaffPushSettingsToggle'
import StaffPushPromptBanner from '../components/StaffPushPromptBanner'
import SupervisorPushPromptTrigger from '../components/SupervisorPushPromptTrigger'
import ThemeToggleButton from '../components/ThemeToggleButton'
import SupervisorAlertsBell from '../components/SupervisorAlertsBell'
import SupervisorClaimsTab from '../components/SupervisorClaimsTab'
import SupervisorHandoverTab from '../components/SupervisorHandoverTab'
import StaffBottomNav, { SUPERVISOR_NAV } from '../components/staff-mobile/StaffBottomNav'
import DropPointChipRow from '../components/staff-mobile/DropPointChipRow'
import StaffMobileBottomSheet from '../components/staff-mobile/StaffMobileBottomSheet'
import StaffDesktopDetailModal from '../components/staff-mobile/StaffDesktopDetailModal'
import { StaffIncomingMobileCard } from '../components/staff-mobile/StaffMobileItemCard'
import { AuthorityLightboxProvider, useAuthorityLightbox } from '../context/AuthorityLightboxContext'
import { MapPin } from 'lucide-react'

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'incoming', label: 'Incoming' },
  { id: 'at-droppoint', label: 'At Drop Point' },
  { id: 'claims', label: 'Claims' },
  { id: 'handover', label: 'Handover' },
  { id: 'authorities', label: 'Authorities' },
  { id: 'redemption', label: 'Redemption' },
  { id: 'settings', label: 'Settings' },
]

const STAFF_ROOT = 'min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100 text-base leading-relaxed'
const STAFF_HEADER = 'border-b border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-950/95'

function TabBadge({ count }) {
  if (!count || count < 1) return null
  return (
    <span className="ml-1.5 inline-flex items-center justify-center min-w-[18px] h-[18px]
                     px-1 text-[10px] font-bold rounded-full bg-red-600 text-white">
      {count > 99 ? '99+' : count}
    </span>
  )
}

function OverviewStat({ label, value }) {
  return (
    <div className="glass rounded-2xl border border-slate-200 dark:border-slate-800/80 p-4">
      <p className="text-xs text-slate-500 uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-1">{value}</p>
    </div>
  )
}

function SupervisorDashboardContent() {
  const { supervisor, logout } = useSupervisorAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const openLightbox = useAuthorityLightbox()
  const [tab, setTab] = useState('overview')
  const [filterDp, setFilterDp] = useState('')
  const [claimsHighlightId, setClaimsHighlightId] = useState(null)
  const [detailItem, setDetailItem] = useState(null)
  const [authForm, setAuthForm] = useState({ email: '', password: '', drop_point_id: '' })
  const [resetPwdId, setResetPwdId] = useState(null)
  const [resetPwd, setResetPwd] = useState('')
  const [redemptionCode, setRedemptionCode] = useState('')
  const [redemptionResult, setRedemptionResult] = useState(null)

  const dropPoints = supervisor?.drop_points || []
  const dpParam = filterDp || undefined

  const overviewQuery = useQuery({
    queryKey: ['supervisor-overview', filterDp],
    queryFn: () => getSupervisorOverview(dpParam),
    enabled: tab === 'overview',
    refetchInterval: tab === 'overview' ? 30_000 : false,
  })

  const incomingQuery = useQuery({
    queryKey: ['supervisor-incoming', filterDp],
    queryFn: () => getSupervisorIncoming(dpParam),
    enabled: tab === 'incoming',
    refetchInterval: tab === 'incoming' ? 30_000 : false,
  })

  const atDpQuery = useQuery({
    queryKey: ['supervisor-at-droppoint', filterDp],
    queryFn: () => getSupervisorAtDroppoint(dpParam),
    enabled: tab === 'at-droppoint',
    refetchInterval: tab === 'at-droppoint' ? 30_000 : false,
  })

  const claimsListQuery = useQuery({
    queryKey: ['supervisor-claims-list', filterDp],
    queryFn: () => getSupervisorClaimsList(dpParam),
    refetchInterval: 30_000,
  })

  const claimsBadge = (claimsListQuery.data?.items || []).reduce(
    (sum, item) => sum + (item.pending_count || 0),
    0
  )

  const authoritiesQuery = useQuery({
    queryKey: ['supervisor-authorities'],
    queryFn: listSupervisorAuthorities,
    enabled: tab === 'authorities',
  })

  const createAuthMutation = useMutation({
    mutationFn: createSupervisorAuthority,
    onSuccess: () => {
      toast.success('Authority created')
      setAuthForm({ email: '', password: '', drop_point_id: '' })
      queryClient.invalidateQueries({ queryKey: ['supervisor-authorities'] })
    },
    onError: (e) => toast.error(e.response?.data?.detail || 'Failed'),
  })

  const toggleAuthMutation = useMutation({
    mutationFn: ({ id, active }) =>
      active ? activateSupervisorAuthority(id) : deactivateSupervisorAuthority(id),
    onSuccess: () => {
      toast.success('Updated')
      queryClient.invalidateQueries({ queryKey: ['supervisor-authorities'] })
    },
    onError: (e) => toast.error(e.response?.data?.detail || 'Failed'),
  })

  const resetPwdMutation = useMutation({
    mutationFn: ({ id, password }) => resetSupervisorAuthorityPassword(id, password),
    onSuccess: () => {
      toast.success('Password reset')
      setResetPwdId(null)
      setResetPwd('')
    },
    onError: (e) => toast.error(e.response?.data?.detail || 'Failed'),
  })

  const handleAlertNavigate = useCallback((parsed) => {
    if (!parsed?.tab) return
    const validTabs = new Set(TABS.map((t) => t.id))
    if (!validTabs.has(parsed.tab)) return
    setTab(parsed.tab)
    if (parsed.tab === 'claims' && parsed.itemId) {
      setClaimsHighlightId(parsed.itemId)
    } else {
      setClaimsHighlightId(null)
    }
  }, [])

  const stats = overviewQuery.data?.stats

  return (
    <div className={STAFF_ROOT}>
      <header className={`hidden md:flex sticky top-0 z-40 ${STAFF_HEADER} px-4 py-3 flex-wrap items-center justify-between gap-3`}>
        <div>
          <h1 className="text-lg font-bold">Supervisor Dashboard</h1>
          <p className="text-xs text-slate-500">{supervisor?.email}</p>
        </div>
        <div className="flex items-center gap-3">
          <ThemeToggleButton />
          <SupervisorAlertsBell onNavigate={handleAlertNavigate} />
          <span className="text-xs text-slate-500">
            {dropPoints.length} drop point{dropPoints.length !== 1 ? 's' : ''} assigned
          </span>
          <button
            type="button"
            onClick={() => { logout(); navigate('/login', { replace: true }) }}
            className="text-xs text-red-500 dark:text-red-400 hover:text-red-600 dark:hover:text-red-300"
          >
            Log out
          </button>
        </div>
      </header>

      <header className={`md:hidden sticky top-0 z-40 ${STAFF_HEADER} px-4 py-3 flex items-center justify-between gap-2`}>
        <div className="min-w-0">
          <h1 className="text-lg font-bold truncate">Supervisor</h1>
          <p className="text-sm text-slate-500 truncate">{supervisor?.email}</p>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <ThemeToggleButton />
          <SupervisorAlertsBell onNavigate={handleAlertNavigate} />
          <button
            type="button"
            onClick={() => { logout(); navigate('/login', { replace: true }) }}
            className="text-sm text-red-500 dark:text-red-400 px-2 min-h-[44px]"
          >
            Out
          </button>
        </div>
      </header>

      <div className={`hidden md:flex gap-1 p-2 border-b border-slate-200 dark:border-slate-800 overflow-x-auto ${STAFF_HEADER}`}>
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`px-3 py-2 text-sm rounded-lg whitespace-nowrap ${
              tab === t.id
                ? 'bg-brand-100 dark:bg-brand-900/40 text-brand-700 dark:text-brand-200'
                : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
            }`}
          >
            {t.label}
            {t.id === 'claims' && <TabBadge count={claimsBadge} />}
          </button>
        ))}
      </div>

      <main className="p-4 max-w-5xl mx-auto space-y-4
                       pb-[calc(5rem+env(safe-area-inset-bottom))] md:pb-8 overflow-x-hidden">
        <DropPointChipRow dropPoints={dropPoints} value={filterDp} onChange={setFilterDp} />

        {tab === 'overview' && (
          <>
            {overviewQuery.isLoading && (
              <div className="flex justify-center py-12">
                <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
              </div>
            )}
            {stats && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <OverviewStat label="Incoming" value={stats.total_incoming} />
                <OverviewStat label="At drop point" value={stats.at_drop_point} />
                <OverviewStat label="Active claims" value={stats.active_claims} />
                <OverviewStat label="Completed handovers" value={stats.completed_handovers} />
              </div>
            )}
          </>
        )}

        {tab === 'incoming' && (
          <>
            {incomingQuery.isLoading && (
              <div className="flex justify-center py-12">
                <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
              </div>
            )}
            {!incomingQuery.isLoading && !(incomingQuery.data?.items?.length) && (
              <p className="text-base text-slate-500">No incoming items in scope.</p>
            )}
            <ul className="space-y-3">
              {(incomingQuery.data?.items || []).map((item) => (
                <li key={item.id}>
                  <StaffIncomingMobileCard
                    item={item}
                    onOpenDetail={setDetailItem}
                    onImageOpen={openLightbox}
                    subtitle={item.drop_point_name}
                    alwaysVisible
                  />
                </li>
              ))}
            </ul>
          </>
        )}

        {tab === 'at-droppoint' && (
          <>
            {atDpQuery.isLoading && (
              <div className="flex justify-center py-12">
                <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
              </div>
            )}
            {!atDpQuery.isLoading && !(atDpQuery.data?.items?.length) && (
              <p className="text-base text-slate-500">No items at drop points in scope.</p>
            )}
            <ul className="space-y-3">
              {(atDpQuery.data?.items || []).map((item) => (
                <li key={item.id}>
                  <StaffIncomingMobileCard
                    item={item}
                    onOpenDetail={setDetailItem}
                    onImageOpen={openLightbox}
                    subtitle={item.drop_point_name}
                    alwaysVisible
                  />
                </li>
              ))}
            </ul>
          </>
        )}

        {tab === 'claims' && (
          <SupervisorClaimsTab filterDp={filterDp} highlightItemId={claimsHighlightId} />
        )}

        {tab === 'handover' && <SupervisorHandoverTab filterDp={filterDp} />}

        {tab === 'authorities' && (
          <div className="space-y-6">
            <form
              className="glass p-4 space-y-3 max-w-lg rounded-2xl"
              onSubmit={(e) => {
                e.preventDefault()
                if (!authForm.email || !authForm.password || !authForm.drop_point_id) {
                  return toast.error('Fill all fields')
                }
                createAuthMutation.mutate({
                  email: authForm.email.trim(),
                  password: authForm.password,
                  drop_point_id: authForm.drop_point_id,
                })
              }}
            >
              <h2 className="text-lg md:text-sm font-semibold">Create authority (in scope)</h2>
              <input type="email" className="input-field w-full min-h-[48px] text-base" placeholder="name@gctu.edu.gh" value={authForm.email} onChange={(e) => setAuthForm((f) => ({ ...f, email: e.target.value }))} />
              <input type="password" className="input-field w-full min-h-[48px] text-base" placeholder="Temporary password" value={authForm.password} onChange={(e) => setAuthForm((f) => ({ ...f, password: e.target.value }))} />
              <select className="input-field w-full min-h-[48px] text-base" value={authForm.drop_point_id} onChange={(e) => setAuthForm((f) => ({ ...f, drop_point_id: e.target.value }))}>
                <option value="">Select drop point</option>
                {dropPoints.map((dp) => (
                  <option key={dp.id} value={dp.id}>{dp.name}</option>
                ))}
              </select>
              <button type="submit" className="btn-primary w-full min-h-[48px] text-base" disabled={createAuthMutation.isPending}>
                Create authority
              </button>
            </form>

            <ul className="space-y-3">
              {(authoritiesQuery.data?.authorities || []).map((a) => (
                <li key={a.id} className="glass p-4 flex flex-wrap items-center justify-between gap-2 border border-slate-200 dark:border-slate-800/80 rounded-2xl">
                  <div>
                    <p className="text-base font-medium">{a.email}</p>
                    <p className="text-sm text-slate-500">{a.drop_point_name}</p>
                  </div>
                  <div className="flex gap-2 flex-wrap w-full md:w-auto">
                    <button type="button" className="btn-secondary text-sm min-h-[44px] flex-1 md:flex-none" onClick={() => setResetPwdId(a.id)}>Reset password</button>
                    <button type="button" className="btn-secondary text-sm min-h-[44px] flex-1 md:flex-none" onClick={() => toggleAuthMutation.mutate({ id: a.id, active: !a.is_active })}>
                      {a.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                  </div>
                  {resetPwdId === a.id && (
                    <form className="w-full flex gap-2 mt-2" onSubmit={(e) => { e.preventDefault(); resetPwdMutation.mutate({ id: a.id, password: resetPwd }) }}>
                      <input type="password" className="input-field flex-1 text-base min-h-[48px]" placeholder="New password" value={resetPwd} onChange={(e) => setResetPwd(e.target.value)} />
                      <button type="submit" className="btn-primary text-sm min-h-[48px]">Save</button>
                    </form>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        {tab === 'redemption' && (
          <div className="glass p-4 max-w-lg space-y-3 rounded-2xl">
            <h2 className="text-lg md:text-sm font-semibold">Redemption lookup</h2>
            <form
              className="flex flex-col sm:flex-row gap-2"
              onSubmit={async (e) => {
                e.preventDefault()
                try {
                  const data = await supervisorLookupRedemptionCode(redemptionCode.trim())
                  setRedemptionResult(data)
                  toast.success(data.message)
                } catch (err) {
                  setRedemptionResult(null)
                  toast.error(err.response?.data?.detail || 'Lookup failed')
                }
              }}
            >
              <input className="input-field flex-1 font-mono uppercase min-h-[48px] text-base" placeholder="FAIND-XXXXXX" value={redemptionCode} onChange={(e) => setRedemptionCode(e.target.value.toUpperCase())} />
              <button type="submit" className="btn-primary text-base min-h-[48px] shrink-0">Redeem</button>
            </form>
            {redemptionResult && (
              <p className="text-base text-slate-700 dark:text-slate-300">{redemptionResult.message}</p>
            )}
          </div>
        )}

        {tab === 'settings' && (
          <div className="glass p-6 max-w-lg rounded-2xl space-y-4">
            <div>
              <p className="text-sm text-slate-500">{supervisor?.email}</p>
            </div>
            <StaffPushSettingsToggle role="supervisor" />
          </div>
        )}

        <p className="hidden md:block text-xs text-slate-500 pt-4">
          <Link to="/" className="hover:text-slate-700 dark:hover:text-slate-400">← Public site</Link>
        </p>
      </main>

      <StaffBottomNav
        items={SUPERVISOR_NAV}
        activeId={tab}
        onChange={setTab}
        badges={{ claims: claimsBadge, incoming: stats?.total_incoming }}
        scrollable
      />

      <StaffMobileBottomSheet
        open={Boolean(detailItem)}
        onClose={() => setDetailItem(null)}
        title={detailItem?.drop_point_name}
      >
        {detailItem && (
          <div className="space-y-3">
            <p className="text-lg font-semibold text-slate-900 dark:text-slate-100">{detailItem.public_description}</p>
            <p className="text-sm text-slate-500">{detailItem.status}</p>
            <p className="text-base text-slate-600 dark:text-slate-400 inline-flex items-center gap-2">
              <MapPin className="w-5 h-5" aria-hidden />
              {detailItem.location_label}
            </p>
          </div>
        )}
      </StaffMobileBottomSheet>

      <StaffDesktopDetailModal
        open={Boolean(detailItem)}
        onClose={() => setDetailItem(null)}
        title={detailItem?.drop_point_name}
      >
        {detailItem && (
          <div className="space-y-3">
            <p className="text-lg font-semibold text-slate-900 dark:text-slate-100">{detailItem.public_description}</p>
            <p className="text-sm text-slate-500">{detailItem.status}</p>
            <p className="text-base text-slate-600 dark:text-slate-400 inline-flex items-center gap-2">
              <MapPin className="w-5 h-5" aria-hidden />
              {detailItem.location_label}
            </p>
          </div>
        )}
      </StaffDesktopDetailModal>

      <SupervisorPushPromptTrigger />
      <StaffPushPromptBanner role="supervisor" enabled />
    </div>
  )
}

export default function SupervisorDashboardPage() {
  return (
    <AuthorityLightboxProvider>
      <SupervisorDashboardContent />
    </AuthorityLightboxProvider>
  )
}
