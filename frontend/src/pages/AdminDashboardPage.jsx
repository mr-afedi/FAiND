/**
 * Admin Dashboard — Feature R (Section 26) with detail panels & notifications.
 */
import { useState, useEffect, useCallback, useMemo } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import AdminNotificationBell from '../components/AdminNotificationBell'
import AdminConfirmDialog from '../components/AdminConfirmDialog'
import {
  formatScorePct,
  statusColor,
  riskTierColor,
  pathBadge,
  EMPTY_STATES,
  ITEM_CATEGORIES,
  formatDateShort,
  formatAdminActionLabel,
  formatAdminLogTarget,
  formatAdminLogDetail,
  formatFraudSignal,
} from '../utils/adminFormat'
import AdminDetailPanel, {
  ClaimDetail,
  DisputeDetail,
  ReportDetail,
  FraudDetail,
  PostDetail,
  ReturnedDetail,
  UserDetailPanel,
} from '../components/AdminDetailPanel'
import {
  adminGate,
  getAnalytics,
  listUsers,
  suspendUser,
  unsuspendUser,
  listClaims,
  approveClaim,
  rejectClaim,
  requestClaimInfo,
  getClaimDetail,
  listDisputes,
  resolveDispute,
  resolveVerificationDispute,
  getDisputeDetail,
  listReports,
  dismissPostReport,
  removeReportedPost,
  dismissUserReport,
  warnUserReport,
  suspendUserReport,
  suppressReporter,
  getReportDetail,
  listFraudAlerts,
  confirmFraud,
  clearFraudFlag,
  allowVerification,
  getFraudDetail,
  listPostsModeration,
  forceClosePost,
  removePost,
  getPostDetail,
  getUserDetail,
  listAdminLogs,
  promoteAdmin,
  demoteAdmin,
  trustAdjustUser,
  lockDisputeItem,
  escalateDispute,
  adminSearch,
  listReturnedItems,
  getReturnedDetail,
  openReturnDispute,
  listUniversities,
  isValidAdminSecret,
  rememberAdminSecret,
  isAdminRole,
} from '../services/adminService'

const POLL_MS = 30_000
const CLAIMS_PAGE_SIZE = 20
const RETURNED_PAGE_SIZE = 20

const NAV = [
  { id: 'overview', label: 'Overview' },
  { id: 'claims', label: 'Claims Review' },
  { id: 'disputes', label: 'Disputes' },
  { id: 'reports', label: 'Reports' },
  { id: 'fraud', label: 'Fraud Alerts' },
  { id: 'posts', label: 'Posts' },
  { id: 'returned', label: 'Returned Items' },
  { id: 'users', label: 'Users' },
  { id: 'logs', label: 'Admin Logs', rootOnly: true },
  { id: 'universities', label: 'Universities', rootOnly: true, future: true },
]

function QueueLoading({ label }) {
  return (
    <div className="flex justify-center py-8">
      <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
      <span className="sr-only">Loading {label}</span>
    </div>
  )
}

function QueueError({ message }) {
  return <p className="text-sm text-red-400 py-4">{message}</p>
}

function EmptyQueue({ section }) {
  return (
    <p className="text-sm text-slate-500 py-8 text-center">
      {EMPTY_STATES[section] || 'Nothing here yet.'}
    </p>
  )
}

function StatCard({ label, value, onClick, highlight }) {
  const Tag = onClick ? 'button' : 'div'
  return (
    <Tag
      type={onClick ? 'button' : undefined}
      onClick={onClick}
      className={`admin-stat w-full transition-colors ${
        onClick ? 'hover:ring-1 hover:ring-brand-500/50 cursor-pointer' : ''
      } ${highlight === 'amber' ? 'ring-1 ring-amber-500/30' : ''}`}
    >
      <p className="text-[10px] text-slate-500 uppercase tracking-wide leading-tight line-clamp-2">{label}</p>
      <p className="text-lg font-bold text-slate-800 dark:text-slate-100 mt-1 tabular-nums">{value}</p>
    </Tag>
  )
}

export default function AdminDashboardPage() {
  const { adminSecret } = useParams()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { user, loading: authLoading, logout, isAuthenticated } = useAuth()
  const { dark, toggle: toggleTheme } = useTheme()
  const queryClient = useQueryClient()

  const [section, setSection] = useState(searchParams.get('section') || 'overview')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [globalSearch, setGlobalSearch] = useState('')
  const [searchDebounced, setSearchDebounced] = useState('')
  const [confirm, setConfirm] = useState(null)
  const [trustAdjustDelta, setTrustAdjustDelta] = useState(0)
  const [trustAdjustReason, setTrustAdjustReason] = useState('')
  const [claimsPage, setClaimsPage] = useState(0)
  const [claimsFilters, setClaimsFilters] = useState({
    path: '',
    score_min: '',
    score_max: '',
    sort: 'created_at_asc',
  })
  const [reportStatus, setReportStatus] = useState('pending')
  const [userFilters, setUserFilters] = useState({ role: '', status: '', trust_tier: '', fraud_tier: '' })
  const [postFilters, setPostFilters] = useState({ status: '', has_reports: '', has_disputes: '' })
  const [returnedPage, setReturnedPage] = useState(0)
  const [returnedFilters, setReturnedFilters] = useState({
    category: '',
    university_id: '',
    date_from: '',
    date_to: '',
    tipped: '',
    sort: 'returned_at_desc',
  })
  const [selectedId, setSelectedId] = useState(searchParams.get('id') || null)
  const [selectedMeta, setSelectedMeta] = useState({
    dispute_type: searchParams.get('dispute_type') || undefined,
    report_type: searchParams.get('report_type') || undefined,
  })
  const [userSearch, setUserSearch] = useState('')
  const [postSearch, setPostSearch] = useState('')
  const [actionNote, setActionNote] = useState('')
  const [disputeOutcome, setDisputeOutcome] = useState('approved')
  const [winnerMatchId, setWinnerMatchId] = useState('')
  const [logFilters, setLogFilters] = useState({
    action: '',
    admin_id: '',
    date_from: '',
    date_to: '',
  })

  if (!isValidAdminSecret(adminSecret)) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-400">
        <p>404 — Not found</p>
      </div>
    )
  }

  rememberAdminSecret(adminSecret)

  useEffect(() => {
    const t = setTimeout(() => setSearchDebounced(globalSearch.trim()), 300)
    return () => clearTimeout(t)
  }, [globalSearch])

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      navigate(`/admin/${adminSecret}/login`, { replace: true })
    } else if (!authLoading && user && !isAdminRole(user.role)) {
      navigate('/', { replace: true })
    }
  }, [authLoading, isAuthenticated, user, navigate, adminSecret])

  const navigateToItem = useCallback((sec, id, meta = {}) => {
    setSection(sec)
    setSelectedId(id)
    setSelectedMeta(meta)
    const params = { section: sec, id }
    if (meta.dispute_type) params.dispute_type = meta.dispute_type
    if (meta.report_type) params.report_type = meta.report_type
    setSearchParams(params)
  }, [setSearchParams])

  const gateQuery = useQuery({
    queryKey: ['admin-gate'],
    queryFn: adminGate,
    enabled: isAuthenticated && isAdminRole(user?.role),
    retry: false,
  })

  const enabled = gateQuery.isSuccess

  const analyticsQuery = useQuery({
    queryKey: ['admin-analytics'],
    queryFn: getAnalytics,
    enabled: section === 'overview' && enabled,
  })

  const usersQuery = useQuery({
    queryKey: ['admin-users', userSearch, userFilters],
    queryFn: () => listUsers({
      search: userSearch || undefined,
      role: userFilters.role || undefined,
      status: userFilters.status || undefined,
      trust_tier: userFilters.trust_tier || undefined,
      fraud_tier: userFilters.fraud_tier || undefined,
      limit: 50,
    }),
    enabled: section === 'users' && enabled,
  })

  const searchQuery = useQuery({
    queryKey: ['admin-search', searchDebounced],
    queryFn: () => adminSearch(searchDebounced),
    enabled: enabled && searchDebounced.length >= 2,
  })

  const claimsQuery = useQuery({
    queryKey: ['admin-claims', claimsPage, claimsFilters],
    queryFn: () => listClaims({
      limit: CLAIMS_PAGE_SIZE,
      offset: claimsPage * CLAIMS_PAGE_SIZE,
      path: claimsFilters.path || undefined,
      score_min: claimsFilters.score_min ? Number(claimsFilters.score_min) : undefined,
      score_max: claimsFilters.score_max ? Number(claimsFilters.score_max) : undefined,
      sort: claimsFilters.sort,
    }),
    enabled: section === 'claims' && enabled,
    refetchInterval: section === 'claims' ? POLL_MS : false,
  })

  const disputesQuery = useQuery({
    queryKey: ['admin-disputes'],
    queryFn: listDisputes,
    enabled: section === 'disputes' && enabled,
    refetchInterval: section === 'disputes' ? POLL_MS : false,
  })

  const reportsQuery = useQuery({
    queryKey: ['admin-reports', reportStatus],
    queryFn: () => listReports(reportStatus),
    enabled: section === 'reports' && enabled,
    refetchInterval: section === 'reports' ? POLL_MS : false,
  })

  const fraudQuery = useQuery({
    queryKey: ['admin-fraud'],
    queryFn: listFraudAlerts,
    enabled: section === 'fraud' && enabled,
  })

  const postsQuery = useQuery({
    queryKey: ['admin-posts', postSearch, postFilters],
    queryFn: () => listPostsModeration({
      search: postSearch || undefined,
      status: postFilters.status || undefined,
      has_reports: postFilters.has_reports === 'yes' ? true : postFilters.has_reports === 'no' ? false : undefined,
      has_disputes: postFilters.has_disputes === 'yes' ? true : postFilters.has_disputes === 'no' ? false : undefined,
      limit: 50,
    }),
    enabled: section === 'posts' && enabled,
  })

  const universitiesQuery = useQuery({
    queryKey: ['universities'],
    queryFn: listUniversities,
    enabled: section === 'returned' && enabled,
    staleTime: 5 * 60_000,
  })

  const returnedQuery = useQuery({
    queryKey: ['admin-returned', returnedPage, returnedFilters],
    queryFn: () => listReturnedItems({
      limit: RETURNED_PAGE_SIZE,
      offset: returnedPage * RETURNED_PAGE_SIZE,
      category: returnedFilters.category || undefined,
      university_id: returnedFilters.university_id || undefined,
      date_from: returnedFilters.date_from || undefined,
      date_to: returnedFilters.date_to || undefined,
      tipped: returnedFilters.tipped === 'yes' ? true : returnedFilters.tipped === 'no' ? false : undefined,
      sort: returnedFilters.sort,
    }),
    enabled: section === 'returned' && enabled,
  })

  const logsQuery = useQuery({
    queryKey: ['admin-logs', logFilters],
    queryFn: () => listAdminLogs({
      action: logFilters.action || undefined,
      admin_id: logFilters.admin_id || undefined,
      date_from: logFilters.date_from || undefined,
      date_to: logFilters.date_to || undefined,
    }),
    enabled: section === 'logs' && enabled && user?.role === 'root_admin',
  })

  const detailQuery = useQuery({
    queryKey: ['admin-detail', section, selectedId, selectedMeta],
    queryFn: async () => {
      if (!selectedId) return null
      switch (section) {
        case 'claims':
          return getClaimDetail(selectedId)
        case 'disputes':
          return getDisputeDetail(selectedId, selectedMeta.dispute_type)
        case 'reports':
          return getReportDetail(selectedId, selectedMeta.report_type)
        case 'fraud':
          return getFraudDetail(selectedId)
        case 'posts':
          return getPostDetail(selectedId)
        case 'users':
          return getUserDetail(selectedId)
        case 'returned':
          return getReturnedDetail(selectedId)
        default:
          return null
      }
    },
    enabled: enabled && !!selectedId && ['claims', 'disputes', 'reports', 'fraud', 'posts', 'users', 'returned'].includes(section),
  })

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['admin'] })
    detailQuery.refetch()
  }

  const openConfirm = (cfg) => setConfirm({ ...cfg, open: true })
  const closeConfirm = () => setConfirm(null)

  const roleLabel = useMemo(() => {
    if (user?.role === 'root_admin') return 'Root Admin'
    if (user?.role === 'assistant_root_admin') return 'Assistant Admin'
    return user?.role || ''
  }, [user?.role])

  const goSection = useCallback((sec, id = null, meta = {}) => {
    setSection(sec)
    setSelectedId(id)
    setSelectedMeta(meta)
    setSidebarOpen(false)
    const params = { section: sec }
    if (id) params.id = id
    if (meta.dispute_type) params.dispute_type = meta.dispute_type
    if (meta.report_type) params.report_type = meta.report_type
    setSearchParams(params)
  }, [setSearchParams])

  const approveClaimMut = useMutation({
    mutationFn: approveClaim,
    onSuccess: (d) => { toast.success(d.message); refresh(); claimsQuery.refetch() },
    onError: (e) => toast.error(e.response?.data?.detail || 'Failed'),
  })

  if (authLoading || gateQuery.isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (gateQuery.isError) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400">
        <p>404 — Not found</p>
      </div>
    )
  }

  const isRoot = user?.role === 'root_admin'
  const a = analyticsQuery.data
  const detail = detailQuery.data

  const actionBtns = (buttons) => (
    <div className="admin-action-row">{buttons}</div>
  )

  const queueItemClass = (selected) =>
    `admin-queue-item ${selected ? 'admin-queue-item-selected' : ''}`

  const renderDetailActions = () => {
    if (!selectedId) return null
    switch (section) {
      case 'claims':
        return actionBtns(
          <>
            <button
              type="button"
              className="btn-primary admin-btn-sm"
              onClick={() => openConfirm({
                title: 'Approve claim?',
                description: 'This unlocks chat between both parties and notifies them. This action is logged permanently.',
                confirmLabel: 'Approve',
                onConfirm: () => approveClaimMut.mutate(selectedId),
              })}
            >
              Approve
            </button>
            <button
              type="button"
              className="btn-secondary admin-btn-sm"
              onClick={() => openConfirm({
                title: 'Reject claim?',
                description: 'The claimant will be notified and a trust penalty may apply per Section 12.6.',
                destructive: true,
                confirmLabel: 'Reject',
                onConfirm: async () => {
                  try {
                    await rejectClaim(selectedId, actionNote || 'Rejected by admin')
                    toast.success('Rejected'); refresh(); claimsQuery.refetch()
                  } catch (e) { toast.error(e.response?.data?.detail || 'Failed') }
                },
              })}
            >
              Reject
            </button>
            <button type="button" className="btn-secondary admin-btn-sm" disabled={actionNote.trim().length < 10} onClick={async () => {
              try {
                await requestClaimInfo(selectedId, actionNote.trim())
                toast.success('Request logged'); setActionNote('')
              } catch (e) { toast.error(e.response?.data?.detail || 'Failed') }
            }}>Request more info</button>
          </>,
        )
      case 'disputes':
        if (selectedMeta.dispute_type === 'verification' || detail?.dispute_type === 'verification') {
          const claimants = detail?.claimants || []
          return actionBtns(
            <>
              <select
                className="admin-select max-w-[11rem]"
                value={winnerMatchId}
                onChange={(e) => setWinnerMatchId(e.target.value)}
              >
                <option value="">Winning claimant…</option>
                {claimants.map((c) => (
                  <option key={c.match_id} value={c.match_id}>
                    {c.claimant?.full_name || 'Unknown'} — {pathBadge(c.path)}
                  </option>
                ))}
              </select>
              <textarea className="admin-textarea flex-1 basis-40" rows={2} placeholder="Note (min 10)" value={actionNote} onChange={(e) => setActionNote(e.target.value)} />
              <button
                type="button"
                className="btn-secondary admin-btn-sm"
                disabled={actionNote.trim().length < 10}
                onClick={() => openConfirm({
                  title: 'Lock item?',
                  description: 'Pauses all pending matches until resolved.',
                  onConfirm: async () => {
                    await lockDisputeItem(selectedId, actionNote.trim(), 'verification')
                    toast.success('Item locked'); refresh()
                  },
                })}
              >
                Lock item
              </button>
              {!isRoot && (
                <button type="button" className="btn-secondary admin-btn-sm" disabled={actionNote.trim().length < 10} onClick={async () => {
                  await escalateDispute(selectedId, actionNote.trim(), 'verification')
                  toast.success('Escalated')
                }}>Escalate to Root</button>
              )}
              <button
                type="button"
                className="btn-primary admin-btn-sm"
                disabled={!winnerMatchId || actionNote.trim().length < 10}
                onClick={async () => {
                  try {
                    await resolveVerificationDispute(selectedId, winnerMatchId, actionNote.trim())
                    toast.success('Verification dispute resolved')
                    setActionNote('')
                    setWinnerMatchId('')
                    refresh()
                    disputesQuery.refetch()
                  } catch (e) { toast.error(e.response?.data?.detail || 'Failed') }
                }}
              >
                Resolve
              </button>
            </>,
          )
        }
        return actionBtns(
          <>
            <select className="admin-select" value={disputeOutcome} onChange={(e) => setDisputeOutcome(e.target.value)}>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="more_info">More info</option>
              <option value="flagged">Flagged</option>
            </select>
            <textarea className="admin-textarea flex-1 basis-40" rows={2} placeholder="Note (min 10)" value={actionNote} onChange={(e) => setActionNote(e.target.value)} />
            <button
              type="button"
              className="btn-secondary admin-btn-sm"
              disabled={actionNote.trim().length < 10}
              onClick={() => openConfirm({
                title: 'Lock item?',
                description: 'No further claims can be submitted on this item until the dispute is resolved.',
                confirmLabel: 'Lock item',
                onConfirm: async () => {
                  try {
                    await lockDisputeItem(selectedId, actionNote.trim(), selectedMeta.dispute_type || detail?.dispute_type)
                    toast.success('Item locked'); refresh()
                  } catch (e) { toast.error(e.response?.data?.detail || 'Failed') }
                },
              })}
            >
              Lock item
            </button>
            {!isRoot && (
              <button
                type="button"
                className="btn-secondary admin-btn-sm"
                disabled={actionNote.trim().length < 10}
                onClick={async () => {
                  try {
                    await escalateDispute(selectedId, actionNote.trim(), selectedMeta.dispute_type || detail?.dispute_type)
                    toast.success('Escalated to root admin')
                  } catch (e) { toast.error(e.response?.data?.detail || 'Failed') }
                }}
              >
                Escalate to Root
              </button>
            )}
            <button type="button" className="btn-primary admin-btn-sm" disabled={actionNote.trim().length < 10} onClick={async () => {
              try {
                await resolveDispute(selectedId, disputeOutcome, actionNote.trim())
                toast.success('Dispute resolved'); setActionNote(''); refresh(); disputesQuery.refetch()
              } catch (e) { toast.error(e.response?.data?.detail || 'Failed') }
            }}>Resolve</button>
          </>,
        )
      case 'reports':
        return actionBtns(
          selectedMeta.report_type === 'post' ? (
            <>
              <button type="button" className="btn-secondary admin-btn-sm" onClick={() => openConfirm({
                title: 'Dismiss report?',
                description: 'This report will be marked dismissed with no action on the post.',
                onConfirm: async () => { await dismissPostReport(selectedId); toast.success('Dismissed'); refresh(); reportsQuery.refetch() },
              })}>Dismiss</button>
              <button type="button" className="btn-primary admin-btn-sm" onClick={() => openConfirm({
                title: 'Remove reported post?',
                description: 'The post will be soft-deleted and hidden from campus. This cannot be undone by the user.',
                destructive: true,
                confirmLabel: 'Remove post',
                onConfirm: async () => { await removeReportedPost(selectedId); toast.success('Post removed'); refresh(); reportsQuery.refetch() },
              })}>Remove post</button>
              <button type="button" className="btn-secondary admin-btn-sm" onClick={async () => {
                const reporterId = detail?.report?.reporter?.id
                if (!reporterId) return
                await suppressReporter(reporterId)
                toast.success('Reporter marked bad faith')
              }}>Mark reporter bad faith</button>
            </>
          ) : (
            <>
              <button type="button" className="btn-secondary admin-btn-sm" onClick={() => openConfirm({
                title: 'Dismiss report?',
                onConfirm: async () => { await dismissUserReport(selectedId); toast.success('Dismissed'); refresh(); reportsQuery.refetch() },
              })}>Dismiss</button>
              <button type="button" className="btn-secondary admin-btn-sm" onClick={() => openConfirm({
                title: 'Warn user?',
                description: 'A community guidelines notification will be sent to the reported user.',
                onConfirm: async () => { await warnUserReport(selectedId); toast.success('Warned'); refresh(); reportsQuery.refetch() },
              })}>Warn user</button>
              <button type="button" className="btn-primary admin-btn-sm" onClick={() => openConfirm({
                title: 'Suspend user?',
                description: 'Their posts will be hidden and chats frozen per Section 4.7.',
                destructive: true,
                confirmLabel: 'Suspend',
                onConfirm: async () => { await suspendUserReport(selectedId); toast.success('Suspended'); refresh(); reportsQuery.refetch() },
              })}>Suspend user</button>
              <button type="button" className="btn-secondary admin-btn-sm" onClick={async () => {
                const reporterId = detail?.report?.reporter?.id
                if (!reporterId) return
                await suppressReporter(reporterId)
                toast.success('Reporter marked bad faith')
              }}>Mark reporter bad faith</button>
            </>
          ),
        )
      case 'fraud':
        return actionBtns(
          <>
            {isRoot && (
              <button type="button" className="btn-primary admin-btn-sm" onClick={() => openConfirm({
                title: 'Confirm fraud?',
                description: 'Trust −20, fraud risk +50. This is logged as admin_confirmed_fraud.',
                destructive: true,
                confirmLabel: 'Confirm fraud',
                onConfirm: async () => {
                  try { await confirmFraud(selectedId); toast.success('Fraud confirmed'); refresh(); fraudQuery.refetch() }
                  catch (e) { toast.error(e.response?.data?.detail || 'Failed') }
                },
              })}>Confirm fraud</button>
            )}
            <button type="button" className="btn-secondary admin-btn-sm" onClick={async () => {
              try { await clearFraudFlag(selectedId); toast.success('Flag cleared'); refresh(); fraudQuery.refetch() }
              catch (e) { toast.error(e.response?.data?.detail || 'Failed') }
            }}>Clear flag</button>
            <button type="button" className="btn-secondary admin-btn-sm" onClick={() => openConfirm({
              title: 'Suspend user?',
              description: 'Posts hidden and chats frozen per Section 4.7.',
              destructive: true,
              confirmLabel: 'Suspend',
              onConfirm: async () => {
                try { await suspendUser(selectedId, 'Fraud review suspension'); toast.success('Suspended'); refresh() }
                catch (e) { toast.error(e.response?.data?.detail || 'Failed') }
              },
            })}>Suspend user</button>
            <button type="button" className="btn-secondary admin-btn-sm" onClick={async () => {
              try { await allowVerification(selectedId); toast.success('Verification allowed'); refresh() }
              catch (e) { toast.error(e.response?.data?.detail || 'Failed') }
            }}>Allow verification</button>
          </>,
        )
      case 'posts':
        return actionBtns(
          <>
            <button type="button" className="btn-secondary admin-btn-sm" onClick={() => openConfirm({
              title: 'Remove post?',
              description: 'Soft-deletes the post and logs the reason. Users cannot restore it.',
              destructive: true,
              confirmLabel: 'Remove',
              onConfirm: async () => {
                try { await removePost(selectedId, actionNote.trim() || 'Admin removal'); toast.success('Removed'); refresh(); postsQuery.refetch() }
                catch (e) { toast.error(e.response?.data?.detail || 'Failed') }
              },
            })}>Remove post</button>
            <button type="button" className="btn-primary admin-btn-sm" onClick={() => openConfirm({
              title: 'Force close post?',
              description: 'Sets status to CLOSED and prevents new matches. Logged permanently.',
              destructive: true,
              confirmLabel: 'Force close',
              onConfirm: async () => {
                try { await forceClosePost(selectedId, actionNote.trim() || 'Admin force close'); toast.success('Force closed'); refresh(); postsQuery.refetch() }
                catch (e) { toast.error(e.response?.data?.detail || 'Failed') }
              },
            })}>Force close</button>
          </>,
        )
      case 'returned':
        if (!detail?.can_open_dispute) return null
        return actionBtns(
          <button
            type="button"
            className="btn-secondary admin-btn-sm"
            disabled={actionNote.trim().length < 10}
            onClick={() => openConfirm({
              title: 'Open dispute on this return?',
              description: 'Creates a manual dispute and sets item status to UNDER_DISPUTE. Both parties will be notified.',
              destructive: true,
              confirmLabel: 'Open dispute',
              onConfirm: async () => {
                try {
                  await openReturnDispute(selectedId, actionNote.trim())
                  toast.success('Dispute opened')
                  setActionNote('')
                  refresh()
                  returnedQuery.refetch()
                  disputesQuery.refetch()
                } catch (e) {
                  toast.error(e.response?.data?.detail || 'Failed')
                }
              },
            })}
          >
            Open dispute
          </button>,
        )
      case 'users': {
        const u = usersQuery.data?.users?.find((x) => x.id === selectedId) || detail?.profile
        return actionBtns(
          <>
            <input type="number" className="admin-input-narrow" placeholder="±" value={trustAdjustDelta} onChange={(e) => setTrustAdjustDelta(Number(e.target.value))} />
            <input className="admin-input-grow" placeholder="Trust reason (min 10)" value={trustAdjustReason} onChange={(e) => setTrustAdjustReason(e.target.value)} />
            <button
              type="button"
              className="btn-secondary admin-btn-sm"
              disabled={!trustAdjustDelta || trustAdjustReason.trim().length < 10}
              onClick={() => openConfirm({
                title: `Adjust trust by ${trustAdjustDelta > 0 ? '+' : ''}${trustAdjustDelta}?`,
                description: trustAdjustReason,
                onConfirm: async () => {
                  try {
                    await trustAdjustUser(selectedId, trustAdjustDelta, trustAdjustReason.trim())
                    toast.success('Trust adjusted'); setTrustAdjustReason(''); refresh(); usersQuery.refetch()
                  } catch (e) { toast.error(e.response?.data?.detail || 'Failed') }
                },
              })}
            >
              Adjust trust
            </button>
            {u?.status === 'active' && u?.role === 'user' && (
              <button type="button" className="btn-secondary admin-btn-sm" onClick={() => openConfirm({
                title: 'Suspend user?',
                description: 'Posts hidden and chats frozen per Section 4.7.',
                destructive: true,
                confirmLabel: 'Suspend',
                onConfirm: async () => {
                  await suspendUser(selectedId, 'Admin suspension'); toast.success('Suspended'); refresh(); usersQuery.refetch()
                },
              })}>Suspend</button>
            )}
            {u?.status === 'suspended' && (
              <button type="button" className="btn-secondary admin-btn-sm" onClick={() => openConfirm({
                title: 'Unsuspend user?',
                description: 'Restores posts, chats, and account access.',
                onConfirm: async () => {
                  await unsuspendUser(selectedId); toast.success('Unsuspended'); refresh(); usersQuery.refetch()
                },
              })}>Unsuspend</button>
            )}
            {isRoot && u?.role === 'user' && (
              <button type="button" className="btn-primary admin-btn-sm" onClick={() => openConfirm({
                title: 'Promote to Assistant Admin?',
                description: 'Max 2 assistant admins enforced. They cannot access Admin Logs or confirm fraud.',
                onConfirm: async () => {
                  try { await promoteAdmin(selectedId); toast.success('Promoted'); usersQuery.refetch() }
                  catch (e) { toast.error(e.response?.data?.detail || 'Failed') }
                },
              })}>Promote</button>
            )}
            {isRoot && u?.role === 'assistant_root_admin' && (
              <button type="button" className="btn-secondary admin-btn-sm" onClick={() => openConfirm({
                title: 'Demote assistant admin?',
                description: 'User returns to regular role immediately.',
                destructive: true,
                confirmLabel: 'Demote',
                onConfirm: async () => {
                  try { await demoteAdmin(selectedId); toast.success('Demoted'); usersQuery.refetch() }
                  catch (e) { toast.error(e.response?.data?.detail || 'Failed') }
                },
              })}>Demote</button>
            )}
          </>,
        )
      }
      default:
        return null
    }
  }

  const renderListItems = () => {
    switch (section) {
      case 'claims':
        return (claimsQuery.data?.claims || []).map((c) => (
          <button key={c.match_id} type="button" onClick={() => navigateToItem('claims', c.match_id)} className={queueItemClass(selectedId === c.match_id)}>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-brand-500/20 text-brand-300">{pathBadge(c.path)}</span>
              <span className={`text-[10px] ${statusColor(c.status)}`}>{c.status.replace(/_/g, ' ')}</span>
            </div>
            <p className="text-sm mt-1 truncate">{c.item_label || c.lost_description}</p>
            <p className="text-xs text-slate-400">{c.claimant_name}</p>
            <p className="text-xs text-slate-500">
              {formatScorePct(c.match_score)} · {c.claimant_trust_tier || '—'} · {new Date(c.created_at).toLocaleDateString()}
            </p>
          </button>
        ))
      case 'disputes':
        return (disputesQuery.data?.disputes || []).map((d) => (
          <button key={`${d.dispute_type}-${d.dispute_id}`} type="button" onClick={() => navigateToItem('disputes', d.dispute_id, { dispute_type: d.dispute_type })} className={queueItemClass(selectedId === d.dispute_id)}>
            <p className="text-xs text-brand-400 uppercase">{d.dispute_type}</p>
            <p className="text-sm">{d.item_label}</p>
            {d.tip_frozen && <p className="text-xs text-amber-400">Tip frozen</p>}
          </button>
        ))
      case 'reports':
        return [...(reportsQuery.data?.reports || [])]
          .sort((a, b) => Number(b.auto_escalated) - Number(a.auto_escalated))
          .map((r) => (
          <button key={r.id} type="button" onClick={() => navigateToItem('reports', r.id, { report_type: r.report_type })} className={queueItemClass(selectedId === r.id)}>
            <p className="text-xs text-brand-400">{r.report_type} · {r.reason}</p>
            {r.auto_escalated && <span className="text-xs text-amber-400">Escalated</span>}
            <p className="text-sm truncate">{r.target_item_description || r.target_user_display_name}</p>
          </button>
        ))
      case 'fraud':
        return (fraudQuery.data?.alerts || []).map((u) => (
          <button key={u.user_id} type="button" onClick={() => navigateToItem('fraud', u.user_id)} className={queueItemClass(selectedId === u.user_id)}>
            <p className="text-sm truncate">
              {u.full_name || u.email}
              {u.username && <span className="text-slate-500"> @{u.username}</span>}
            </p>
            <p className="text-xs mt-0.5">
              Risk {u.fraud_risk_score}{' '}
              <span className={`px-1.5 py-0.5 rounded ${riskTierColor(u.risk_tier)}`}>{u.risk_tier}</span>
              {' · '}Trust {u.trust_score}
              {u.verification_blocked && <span className="text-red-400"> · Blocked</span>}
              {u.fraud_verification_override && <span className="text-emerald-400"> · Override</span>}
            </p>
            {u.last_signal && (
              <p className="text-[10px] text-slate-500 mt-0.5 truncate">
                Last signal: {formatFraudSignal(u.last_signal)}
              </p>
            )}
          </button>
        ))
      case 'posts':
        return (postsQuery.data?.posts || []).map((p) => (
          <button key={p.item_id} type="button" onClick={() => navigateToItem('posts', p.item_id)} className={queueItemClass(selectedId === p.item_id)}>
            <div className="flex items-center gap-2 flex-wrap">
              <p className="text-xs text-slate-400">{p.item_type} · {p.status}</p>
              {p.flagged && <span className="text-[10px] text-amber-400 uppercase">Flagged</span>}
              {p.pending_reports > 0 && (
                <span className="text-[10px] text-red-400">{p.pending_reports} report{p.pending_reports !== 1 ? 's' : ''}</span>
              )}
            </div>
            <p className="text-sm truncate">{p.public_description}</p>
            <p className="text-xs text-slate-500 truncate">{p.posted_by_name}</p>
          </button>
        ))
      case 'users':
        return (usersQuery.data?.users || []).map((u) => (
          <button key={u.id} type="button" onClick={() => navigateToItem('users', u.id)} className={queueItemClass(selectedId === u.id)}>
            <p className="text-sm">{u.full_name} <span className="text-slate-500">@{u.username}</span></p>
            <p className="text-xs text-slate-400 truncate">{u.email}</p>
            <p className="text-xs text-slate-500 mt-0.5">
              Trust {u.trust_score} · Risk {u.fraud_risk_score}
              {' · '}
              <span className={statusColor(u.status)}>{u.status}</span>
              {' · '}{u.role.replace(/_/g, ' ')}
            </p>
          </button>
        ))
      case 'returned':
        return (returnedQuery.data?.items || []).map((r) => (
          <button
            key={r.return_id}
            type="button"
            onClick={() => navigateToItem('returned', r.return_id)}
            className={queueItemClass(selectedId === r.return_id)}
          >
            <p className="text-sm truncate font-medium">{r.item_description}</p>
            <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 mt-1 text-[11px] text-slate-500">
              <span><span className="text-slate-400">Category</span> {r.category.replace(/_/g, ' ')}</span>
              <span><span className="text-slate-400">Tipped</span> {r.tipped ? 'Yes' : 'No'}</span>
              <span className="truncate"><span className="text-slate-400">Owner</span> @{r.owner_username}</span>
              <span className="truncate"><span className="text-slate-400">Finder</span> @{r.finder_username}</span>
              <span><span className="text-slate-400">Lost</span> {formatDateShort(r.date_lost)}</span>
              <span><span className="text-slate-400">Found</span> {formatDateShort(r.date_found)}</span>
              <span className="col-span-2"><span className="text-slate-400">Returned</span> {formatDateShort(r.date_returned)}</span>
            </div>
          </button>
        ))
      default:
        return []
    }
  }

  const listItems = renderListItems()

  const renderDetailContent = () => {
    if (detailQuery.isLoading) {
      return <p className="text-sm text-slate-500">Loading…</p>
    }
    if (detailQuery.isError) {
      return (
        <p className="text-sm text-red-400">
          Failed to load details: {detailQuery.error?.response?.data?.detail || detailQuery.error?.message || 'Unknown error'}
        </p>
      )
    }
    const actions = renderDetailActions()
    switch (section) {
      case 'claims':
        return <ClaimDetail detail={detail} actions={<>{actions}<textarea className="admin-textarea w-full mt-2" rows={2} placeholder="Note for reject / request info (min 10 chars)" value={actionNote} onChange={(e) => setActionNote(e.target.value)} /></>} />
      case 'disputes':
        return <DisputeDetail detail={detail} actions={actions} />
      case 'reports':
        return <ReportDetail detail={detail} actions={actions} />
      case 'fraud':
        return <FraudDetail detail={detail} actions={actions} />
      case 'posts':
        return <PostDetail detail={detail} actions={actions} />
      case 'users':
        return <UserDetailPanel detail={detail} actions={actions} />
      case 'returned':
        return (
          <ReturnedDetail
            detail={detail}
            actions={(
              <>
                {actions}
                {detail?.can_open_dispute && (
                  <textarea
                    className="admin-textarea w-full mt-2"
                    rows={2}
                    placeholder="Reason for opening dispute (min 10 chars)"
                    value={actionNote}
                    onChange={(e) => setActionNote(e.target.value)}
                  />
                )}
              </>
            )}
            onGoToDispute={(id, disputeType) => goSection('disputes', id, { dispute_type: disputeType })}
          />
        )
      default:
        return null
    }
  }

  const hasSplit = ['claims', 'disputes', 'reports', 'fraud', 'posts', 'returned', 'users'].includes(section)

  const navItems = NAV.filter((n) => !n.rootOnly || isRoot)

  const queueQuery = {
    claims: claimsQuery,
    disputes: disputesQuery,
    reports: reportsQuery,
    fraud: fraudQuery,
    posts: postsQuery,
    returned: returnedQuery,
    users: usersQuery,
  }[section]

  return (
    <div className="min-h-screen bg-slate-100 dark:bg-slate-950 text-slate-800 dark:text-slate-200 flex">
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 bg-black/50 lg:hidden" onClick={() => setSidebarOpen(false)} aria-hidden />
      )}
      <aside className={`fixed lg:static inset-y-0 left-0 z-50 w-56 border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 p-4 flex flex-col gap-1 shrink-0 transform transition-transform ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}>
        <p className="text-xs font-semibold text-brand-500 dark:text-brand-400 mb-3 px-2">FAiND Admin</p>
        {navItems.map((item) => (
          <button
            key={item.id}
            type="button"
            disabled={item.future}
            onClick={() => {
              if (item.future) return
              goSection(item.id)
            }}
            className={`text-left px-3 py-2 rounded-lg text-sm transition-colors ${
              section === item.id ? 'bg-brand-600/20 text-brand-600 dark:text-brand-300' : 'text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
            } ${item.future ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            {item.label}{item.future ? ' (soon)' : ''}
          </button>
        ))}
        <div className="mt-auto pt-4 border-t border-slate-200 dark:border-slate-800">
          <Link to="/" className="block text-xs text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 px-2">← Main site</Link>
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-h-screen min-w-0">
        <header className="border-b border-slate-200 dark:border-slate-800 px-4 lg:px-5 py-2 flex items-center gap-2 shrink-0 bg-white/90 dark:bg-slate-950/90 backdrop-blur sticky top-0 z-30">
          <button type="button" className="lg:hidden btn-secondary text-xs !py-1 !px-2.5" onClick={() => setSidebarOpen(true)}>Menu</button>
          <h1 className="text-base font-bold capitalize shrink-0 hidden sm:block">{section.replace('_', ' ')}</h1>
          <div className="relative w-44 sm:w-52 md:w-60 ml-auto">
            <input
              className="admin-input-search w-full"
              placeholder="Search…"
              value={globalSearch}
              onChange={(e) => setGlobalSearch(e.target.value)}
            />
            {searchDebounced.length >= 2 && searchQuery.data && (
              <div className="absolute top-full mt-1 w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-lg z-50 max-h-64 overflow-y-auto text-xs">
                {searchQuery.data.users?.map((u) => (
                  <button key={u.id} type="button" className="w-full text-left px-3 py-2 hover:bg-slate-50 dark:hover:bg-slate-800" onClick={() => { setGlobalSearch(''); goSection('users', u.id) }}>
                    <span className="text-slate-700 dark:text-slate-200">User</span> · {u.full_name} ({u.email})
                  </button>
                ))}
                {searchQuery.data.items?.map((i) => (
                  <button key={i.id} type="button" className="w-full text-left px-3 py-2 hover:bg-slate-50 dark:hover:bg-slate-800" onClick={() => { setGlobalSearch(''); goSection('posts', i.id) }}>
                    <span className="text-slate-700 dark:text-slate-200">Item</span> · {i.public_description}
                  </button>
                ))}
                {searchQuery.data.claims?.map((c) => (
                  <button key={c.match_id} type="button" className="w-full text-left px-3 py-2 hover:bg-slate-50 dark:hover:bg-slate-800" onClick={() => { setGlobalSearch(''); goSection('claims', c.match_id) }}>
                    <span className="text-slate-700 dark:text-slate-200">Claim</span> · {c.claimant_name} {formatScorePct(c.match_score)}
                  </button>
                ))}
                {!searchQuery.data.users?.length && !searchQuery.data.items?.length && !searchQuery.data.claims?.length && (
                  <p className="px-3 py-3 text-slate-500">No results</p>
                )}
              </div>
            )}
          </div>
          <span className="hidden md:inline text-[10px] px-2 py-0.5 rounded-md bg-brand-500/10 text-brand-600 dark:text-brand-300 font-medium whitespace-nowrap">
            {roleLabel}
          </span>
          <button type="button" className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 shrink-0" onClick={toggleTheme} aria-label="Toggle theme">
            {dark ? '☀️' : '🌙'}
          </button>
          <AdminNotificationBell onNavigate={navigateToItem} />
          <button type="button" className="text-xs text-red-500 hover:text-red-400 px-1.5 shrink-0" onClick={() => logout()}>Logout</button>
        </header>

        <main className="flex-1 p-4 lg:p-6 overflow-hidden flex flex-col">
          {section === 'universities' && (
            <div className="glass p-8 text-center text-slate-500">
              <p className="text-lg font-medium text-slate-700 dark:text-slate-300">Universities & campus zones</p>
              <p className="text-sm mt-2">Coming soon — root admin will manage universities and campus zones here.</p>
            </div>
          )}

          {section === 'overview' && (
            analyticsQuery.isLoading ? <QueueLoading label="analytics" />
              : analyticsQuery.isError ? <QueueError message="Failed to load analytics." />
              : a && (
            <div className="overflow-y-auto space-y-4">
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-2">
                <StatCard label="Lost items (all)" value={a.total_lost_items} />
                <StatCard label="Found items (all)" value={a.total_found_items} />
                <StatCard label="Returned (all)" value={a.total_returned} />
                <StatCard label="Return rate" value={`${a.return_rate_percent}%`} />
                <StatCard label="Lost this week" value={a.lost_items_this_week} />
                <StatCard label="Found this week" value={a.found_items_this_week} />
                <StatCard label="Returned this week" value={a.returned_this_week} />
                <StatCard label="Avg days post→return" value={a.avg_days_post_to_return ?? '—'} />
                <StatCard label="Claims Path A" value={a.claims_path_a} />
                <StatCard label="Claims Path B" value={a.claims_path_b} />
                <StatCard label="Claims Path C" value={a.claims_path_c} />
                <StatCard label="Disputes open / resolved" value={`${a.disputes_opened_total} / ${a.disputes_resolved_total}`} />
                <StatCard label="Active users D/W/M" value={`${a.active_users_daily}/${a.active_users_weekly}/${a.active_users_monthly}`} />
                <StatCard label="Fraud events (wk)" value={a.fraud_events_this_week} />
                <StatCard label="Claims in review" value={a.claims_pending_review} highlight="amber" onClick={() => goSection('claims')} />
                <StatCard label="Open disputes" value={a.disputes_open} highlight="amber" onClick={() => goSection('disputes')} />
                <StatCard label="Pending reports" value={a.reports_pending} highlight="amber" onClick={() => goSection('reports')} />
                <StatCard label="Fraud alerts" value={a.fraud_alerts} highlight="amber" onClick={() => goSection('fraud')} />
              </div>
              {a.trust_distribution && (
                <div className="admin-stat p-3">
                  <p className="text-[10px] text-slate-500 uppercase mb-2">Trust score distribution</p>
                  <div className="grid grid-cols-4 gap-2">
                    {Object.entries(a.trust_distribution).map(([tier, count]) => (
                      <div key={tier} className="text-center">
                        <p className="text-2xl font-bold text-slate-800 dark:text-slate-100">{count}</p>
                        <p className="text-[10px] text-slate-500 uppercase mt-1">{tier.replace(/_/g, ' ')}</p>
                        <div className="h-1.5 mt-2 rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden">
                          <div className="h-full bg-brand-500 rounded-full" style={{ width: `${Math.min(100, (count / Math.max(1, Object.values(a.trust_distribution).reduce((s, v) => s + v, 0))) * 100)}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}

          {section === 'claims' && hasSplit && (
            <div className="admin-toolbar">
              <select className="admin-select" value={claimsFilters.path} onChange={(e) => { setClaimsPage(0); setClaimsFilters((f) => ({ ...f, path: e.target.value })) }}>
                <option value="">All paths</option>
                <option value="path_a">Path A</option>
                <option value="path_b">Path B</option>
                <option value="path_c">Path C</option>
              </select>
              <input className="admin-input-narrow" placeholder="Min" value={claimsFilters.score_min} onChange={(e) => setClaimsFilters((f) => ({ ...f, score_min: e.target.value }))} />
              <input className="admin-input-narrow" placeholder="Max" value={claimsFilters.score_max} onChange={(e) => setClaimsFilters((f) => ({ ...f, score_max: e.target.value }))} />
              <select className="admin-select" value={claimsFilters.sort} onChange={(e) => setClaimsFilters((f) => ({ ...f, sort: e.target.value }))}>
                <option value="created_at_asc">Oldest</option>
                <option value="created_at_desc">Newest</option>
                <option value="score_desc">High score</option>
                <option value="score_asc">Low score</option>
              </select>
              {claimsQuery.data?.total != null && (
                <span className="text-[10px] text-slate-500 whitespace-nowrap">{claimsQuery.data.total} in queue</span>
              )}
            </div>
          )}

          {section === 'reports' && hasSplit && (
            <div className="admin-toolbar">
              <select className="admin-select" value={reportStatus} onChange={(e) => setReportStatus(e.target.value)}>
                <option value="pending">Pending</option>
                <option value="all">All</option>
                <option value="dismissed">Dismissed</option>
                <option value="resolved">Resolved</option>
              </select>
            </div>
          )}

          {section === 'users' && hasSplit && (
            <div className="admin-toolbar">
              <input className="admin-input-wide" placeholder="Search users…" value={userSearch} onChange={(e) => setUserSearch(e.target.value)} />
              <select className="admin-select" value={userFilters.role} onChange={(e) => setUserFilters((f) => ({ ...f, role: e.target.value }))}>
                <option value="">All roles</option>
                <option value="user">User</option>
                <option value="assistant_root_admin">Assistant</option>
                <option value="root_admin">Root</option>
              </select>
              <select className="admin-select" value={userFilters.status} onChange={(e) => setUserFilters((f) => ({ ...f, status: e.target.value }))}>
                <option value="">All status</option>
                <option value="active">Active</option>
                <option value="suspended">Suspended</option>
              </select>
            </div>
          )}

          {section === 'posts' && hasSplit && (
            <div className="admin-toolbar">
              <input className="admin-input-wide" placeholder="Search posts…" value={postSearch} onChange={(e) => setPostSearch(e.target.value)} />
              <select className="admin-select" value={postFilters.status} onChange={(e) => setPostFilters((f) => ({ ...f, status: e.target.value }))}>
                <option value="">All status</option>
                <option value="active">Active</option>
                <option value="under_dispute">Disputed</option>
                <option value="potential_match">Matched</option>
              </select>
              <select className="admin-select" value={postFilters.has_reports} onChange={(e) => setPostFilters((f) => ({ ...f, has_reports: e.target.value }))}>
                <option value="">Reports</option>
                <option value="yes">Has reports</option>
                <option value="no">No reports</option>
              </select>
              {postsQuery.data?.total != null && (
                <span className="text-[10px] text-slate-500 whitespace-nowrap">{postsQuery.data.total} posts</span>
              )}
            </div>
          )}

          {section === 'returned' && hasSplit && (
            <div className="admin-toolbar">
              <select
                className="admin-select"
                value={returnedFilters.category}
                onChange={(e) => {
                  setReturnedPage(0)
                  setReturnedFilters((f) => ({ ...f, category: e.target.value }))
                }}
              >
                <option value="">All categories</option>
                {ITEM_CATEGORIES.map((cat) => (
                  <option key={cat} value={cat}>{cat.replace(/_/g, ' ')}</option>
                ))}
              </select>
              <select
                className="admin-select"
                value={returnedFilters.university_id}
                onChange={(e) => {
                  setReturnedPage(0)
                  setReturnedFilters((f) => ({ ...f, university_id: e.target.value }))
                }}
              >
                <option value="">All universities</option>
                {(universitiesQuery.data || []).map((u) => (
                  <option key={u.id} value={u.id}>{u.name}</option>
                ))}
              </select>
              <input
                type="date"
                className="admin-input"
                value={returnedFilters.date_from}
                onChange={(e) => {
                  setReturnedPage(0)
                  setReturnedFilters((f) => ({ ...f, date_from: e.target.value }))
                }}
              />
              <input
                type="date"
                className="admin-input"
                value={returnedFilters.date_to}
                onChange={(e) => {
                  setReturnedPage(0)
                  setReturnedFilters((f) => ({ ...f, date_to: e.target.value }))
                }}
              />
              <select
                className="admin-select"
                value={returnedFilters.tipped}
                onChange={(e) => {
                  setReturnedPage(0)
                  setReturnedFilters((f) => ({ ...f, tipped: e.target.value }))
                }}
              >
                <option value="">All tips</option>
                <option value="yes">Tipped</option>
                <option value="no">Not tipped</option>
              </select>
              <select
                className="admin-select"
                value={returnedFilters.sort}
                onChange={(e) => setReturnedFilters((f) => ({ ...f, sort: e.target.value }))}
              >
                <option value="returned_at_desc">Returned (newest)</option>
                <option value="returned_at_asc">Returned (oldest)</option>
                <option value="date_lost_desc">Date lost (newest)</option>
                <option value="date_lost_asc">Date lost (oldest)</option>
                <option value="date_found_desc">Date found (newest)</option>
                <option value="date_found_asc">Date found (oldest)</option>
                <option value="category_asc">Category A–Z</option>
                <option value="category_desc">Category Z–A</option>
                <option value="owner_asc">Owner A–Z</option>
                <option value="finder_asc">Finder A–Z</option>
                <option value="tipped_desc">Tipped first</option>
                <option value="tipped_asc">Not tipped first</option>
              </select>
              {returnedQuery.data?.total != null && (
                <span className="text-[10px] text-slate-500 whitespace-nowrap">{returnedQuery.data.total} returned</span>
              )}
            </div>
          )}

          {section === 'logs' && isRoot && (
            <div className="space-y-2 overflow-y-auto">
              <div className="admin-toolbar mb-2">
                <input className="admin-input-wide" placeholder="Action type" value={logFilters.action} onChange={(e) => setLogFilters((f) => ({ ...f, action: e.target.value }))} />
                <input className="admin-input-wide" placeholder="Admin UUID" value={logFilters.admin_id} onChange={(e) => setLogFilters((f) => ({ ...f, admin_id: e.target.value }))} />
                <input type="date" className="admin-input" value={logFilters.date_from} onChange={(e) => setLogFilters((f) => ({ ...f, date_from: e.target.value }))} />
                <input type="date" className="admin-input" value={logFilters.date_to} onChange={(e) => setLogFilters((f) => ({ ...f, date_to: e.target.value }))} />
              </div>
              {logsQuery.isLoading && <QueueLoading label="logs" />}
              {logsQuery.isError && <QueueError message="Failed to load admin logs." />}
              <div className="space-y-2 text-sm max-h-[70vh] overflow-y-auto">
                {(logsQuery.data?.logs || []).map((log) => {
                  const detailText = formatAdminLogDetail(log)
                  return (
                    <div key={log.id} className="admin-queue-item">
                      <p className="text-slate-300">
                        <span className="text-brand-400">{formatAdminActionLabel(log.action)}</span>
                        {' · '}
                        {log.admin_email || 'system'}
                      </p>
                      <p className="text-xs text-slate-500">
                        {formatAdminLogTarget(log)}
                        {' · '}
                        {new Date(log.created_at).toLocaleString()}
                      </p>
                      {detailText && (
                        <p className="text-xs text-slate-400 mt-1 leading-relaxed">{detailText}</p>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {hasSplit && (
            <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)] gap-3 flex-1 min-h-0 items-start">
              <div className="flex flex-col gap-1 overflow-y-auto max-h-[calc(100vh-11rem)] min-w-0">
                {queueQuery?.isLoading && <QueueLoading label={section} />}
                {queueQuery?.isError && (
                  <QueueError message={queueQuery.error?.response?.data?.detail || queueQuery.error?.message || 'Failed to load queue.'} />
                )}
                {!queueQuery?.isLoading && !queueQuery?.isError && listItems}
                {!queueQuery?.isLoading && !queueQuery?.isError && listItems.length === 0 && (
                  <EmptyQueue section={section} />
                )}
                {section === 'claims' && claimsQuery.data?.total > CLAIMS_PAGE_SIZE && (
                  <div className="flex gap-2 pt-2">
                    <button type="button" className="btn-secondary text-xs py-1" disabled={claimsPage === 0} onClick={() => setClaimsPage((p) => p - 1)}>Prev</button>
                    <span className="text-xs text-slate-500 self-center">Page {claimsPage + 1}</span>
                    <button type="button" className="btn-secondary text-xs py-1" disabled={(claimsPage + 1) * CLAIMS_PAGE_SIZE >= claimsQuery.data.total} onClick={() => setClaimsPage((p) => p + 1)}>Next</button>
                  </div>
                )}
                {section === 'returned' && returnedQuery.data?.total > RETURNED_PAGE_SIZE && (
                  <div className="flex gap-2 pt-2">
                    <button type="button" className="btn-secondary text-xs py-1" disabled={returnedPage === 0} onClick={() => setReturnedPage((p) => p - 1)}>Prev</button>
                    <span className="text-xs text-slate-500 self-center">
                      Page {returnedPage + 1} of {Math.ceil(returnedQuery.data.total / RETURNED_PAGE_SIZE)}
                    </span>
                    <button
                      type="button"
                      className="btn-secondary text-xs py-1"
                      disabled={(returnedPage + 1) * RETURNED_PAGE_SIZE >= returnedQuery.data.total}
                      onClick={() => setReturnedPage((p) => p + 1)}
                    >
                      Next
                    </button>
                  </div>
                )}
              </div>
              <AdminDetailPanel section={section} detail={selectedId ? detail : null} loading={detailQuery.isLoading}>
                {renderDetailContent()}
              </AdminDetailPanel>
            </div>
          )}
        </main>
      </div>

      <AdminConfirmDialog
        open={!!confirm?.open}
        title={confirm?.title}
        description={confirm?.description}
        confirmLabel={confirm?.confirmLabel}
        destructive={confirm?.destructive}
        onCancel={closeConfirm}
        onConfirm={async () => {
          try {
            await confirm?.onConfirm?.()
          } finally {
            closeConfirm()
          }
        }}
      />
    </div>
  )
}
