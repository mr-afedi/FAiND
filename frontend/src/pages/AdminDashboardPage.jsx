/**
 * Admin Dashboard — Feature R (Section 26) with detail panels & notifications.
 */
import { useState, useEffect, useCallback, useMemo } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useAuth } from '../context/AuthContext'
import AdminNotificationBell from '../components/AdminNotificationBell'
import ThemeToggleButton from '../components/ThemeToggleButton'
import AdminConfirmDialog from '../components/AdminConfirmDialog'
import {
  statusColor,
  EMPTY_STATES,
  ITEM_CATEGORIES,
  formatDateShort,
  formatAdminActionLabel,
  formatAdminLogTarget,
  formatAdminLogDetail,
} from '../utils/adminFormat'
import AdminDetailPanel, {
  DisputeDetail,
  ReportDetail,
  PostDetail,
  ReturnedDetail,
  UserDetailPanel,
  ClaimDetail,
} from '../components/AdminDetailPanel'
import {
  adminGate,
  getAnalytics,
  listUsers,
  suspendUser,
  unsuspendUser,
  listDisputes,
  resolveDispute,
  getDisputeDetail,
  listReports,
  dismissPostReport,
  removeReportedPost,
  dismissUserReport,
  warnUserReport,
  suspendUserReport,
  suppressReporter,
  getReportDetail,
  listPostsModeration,
  forceClosePost,
  removePost,
  getPostDetail,
  getUserDetail,
  listAdminLogs,
  lockDisputeItem,
  escalateDispute,
  adminSearch,
  listReturnedItems,
  getReturnedDetail,
  openReturnDispute,
  listUniversities,
  listAuthorities,
  createAuthority,
  deactivateAuthority,
  activateAuthority,
  lookupRedemptionCode,
  listSupervisors,
  createSupervisor,
  updateSupervisor,
  listAdminDropPoints,
  createAdminDropPoint,
  updateAdminDropPoint,
  listClaimsOverview,
  getClaimOverviewDetail,
  reassignAuthority,
  getTokenSettings,
  updateTokenSettings,
  isValidAdminSecret,
  rememberAdminSecret,
  isAdminRole,
} from '../services/adminService'
import { listDropPoints } from '../services/dropPointService'
import StaffPushSettingsToggle from '../components/StaffPushSettingsToggle'
import StaffPushPromptBanner from '../components/StaffPushPromptBanner'
import AdminPushPromptTrigger from '../components/AdminPushPromptTrigger'

const POLL_MS = 30_000
const RETURNED_PAGE_SIZE = 20

const NAV = [
  { id: 'overview', label: 'Overview' },
  { id: 'drop_points', label: 'Drop Points', rootOnly: true },
  { id: 'authorities', label: 'Authorities', rootOnly: true },
  { id: 'supervisors', label: 'Supervisors', rootOnly: true },
  { id: 'claims', label: 'Claims Overview', rootOnly: true },
  { id: 'returned', label: 'Returned Items' },
  { id: 'token_settings', label: 'Token Settings', rootOnly: true },
  { id: 'redemption', label: 'Redemption Lookup', rootOnly: true },
  { id: 'logs', label: 'Admin Logs', rootOnly: true },
  { id: 'settings', label: 'Settings' },
  { id: 'disputes', label: 'Disputes' },
  { id: 'reports', label: 'Reports' },
  { id: 'posts', label: 'Posts' },
  { id: 'users', label: 'Users' },
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
  const queryClient = useQueryClient()

  const [section, setSection] = useState(searchParams.get('section') || 'overview')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [globalSearch, setGlobalSearch] = useState('')
  const [searchDebounced, setSearchDebounced] = useState('')
  const [confirm, setConfirm] = useState(null)
  const [reportStatus, setReportStatus] = useState('pending')
  const [userFilters, setUserFilters] = useState({ role: '', status: '' })
  const [postFilters, setPostFilters] = useState({ status: '', has_reports: '', has_disputes: '' })
  const [returnedPage, setReturnedPage] = useState(0)
  const [returnedFilters, setReturnedFilters] = useState({
    category: '',
    university_id: '',
    date_from: '',
    date_to: '',
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
  const [logFilters, setLogFilters] = useState({
    action: '',
    admin_id: '',
    date_from: '',
    date_to: '',
  })
  const [authorityForm, setAuthorityForm] = useState({ email: '', password: '', drop_point_id: '' })
  const [creatingAuthority, setCreatingAuthority] = useState(false)
  const [redemptionCode, setRedemptionCode] = useState('')
  const [redemptionResult, setRedemptionResult] = useState(null)
  const [redemptionLoading, setRedemptionLoading] = useState(false)
  const [supervisorForm, setSupervisorForm] = useState({
    email: '', password: '', university_id: '', drop_point_ids: [],
  })
  const [creatingSupervisor, setCreatingSupervisor] = useState(false)
  const [dropPointForm, setDropPointForm] = useState({
    university_id: '', name: '', type: 'faculty', latitude: '', longitude: '', operating_hours: 'Mon-Fri 08:00-17:00',
  })
  const [editingDropPoint, setEditingDropPoint] = useState(null)
  const [dropPointEditForm, setDropPointEditForm] = useState({})
  const [creatingDropPoint, setCreatingDropPoint] = useState(false)
  const [tokenSettingsForm, setTokenSettingsForm] = useState(null)
  const [savingTokenSettings, setSavingTokenSettings] = useState(false)
  const [reassignAuthId, setReassignAuthId] = useState(null)
  const [reassignDropPointId, setReassignDropPointId] = useState('')
  const [claimsFilter, setClaimsFilter] = useState('')

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
      navigate('/login', { replace: true })
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
      limit: 50,
    }),
    enabled: section === 'users' && enabled,
  })

  const searchQuery = useQuery({
    queryKey: ['admin-search', searchDebounced],
    queryFn: () => adminSearch(searchDebounced),
    enabled: enabled && searchDebounced.length >= 2,
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
    enabled: enabled && ['returned', 'supervisors', 'drop_points'].includes(section),
    staleTime: 5 * 60_000,
  })

  const dropPointsQuery = useQuery({
    queryKey: ['admin-drop-points'],
    queryFn: listAdminDropPoints,
    enabled: section === 'drop_points' && enabled && user?.role === 'root_admin',
  })

  const claimsQuery = useQuery({
    queryKey: ['admin-claims-overview'],
    queryFn: listClaimsOverview,
    enabled: section === 'claims' && enabled && user?.role === 'root_admin',
  })

  const tokenSettingsQuery = useQuery({
    queryKey: ['admin-token-settings'],
    queryFn: getTokenSettings,
    enabled: section === 'token_settings' && enabled && user?.role === 'root_admin',
  })

  useEffect(() => {
    if (tokenSettingsQuery.data && section === 'token_settings') {
      setTokenSettingsForm({
        found_item_posted: tokenSettingsQuery.data.found_item_posted,
        drop_off_on_time: tokenSettingsQuery.data.drop_off_on_time,
        drop_off_late: tokenSettingsQuery.data.drop_off_late,
        item_claimed: tokenSettingsQuery.data.item_claimed,
      })
    }
  }, [tokenSettingsQuery.data, section])

  const returnedQuery = useQuery({
    queryKey: ['admin-returned', returnedPage, returnedFilters],
    queryFn: () => listReturnedItems({
      limit: RETURNED_PAGE_SIZE,
      offset: returnedPage * RETURNED_PAGE_SIZE,
      category: returnedFilters.category || undefined,
      university_id: returnedFilters.university_id || undefined,
      date_from: returnedFilters.date_from || undefined,
      date_to: returnedFilters.date_to || undefined,
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

  const authoritiesQuery = useQuery({
    queryKey: ['admin-authorities'],
    queryFn: listAuthorities,
    enabled: section === 'authorities' && enabled && user?.role === 'root_admin',
  })

  const authDropPointsQuery = useQuery({
    queryKey: ['admin-auth-drop-points'],
    queryFn: listAdminDropPoints,
    enabled: (section === 'authorities' || Boolean(reassignAuthId)) && enabled && user?.role === 'root_admin',
  })

  const supervisorsQuery = useQuery({
    queryKey: ['admin-supervisors'],
    queryFn: listSupervisors,
    enabled: section === 'supervisors' && enabled && user?.role === 'root_admin',
  })

  const supervisorDropPointsQuery = useQuery({
    queryKey: ['admin-supervisor-drop-points', supervisorForm.university_id],
    queryFn: () => listDropPoints(supervisorForm.university_id),
    enabled: section === 'supervisors' && enabled && Boolean(supervisorForm.university_id),
  })

  const detailQuery = useQuery({
    queryKey: ['admin-detail', section, selectedId, selectedMeta],
    queryFn: async () => {
      if (!selectedId) return null
      switch (section) {
        case 'disputes':
          return getDisputeDetail(selectedId, selectedMeta.dispute_type)
        case 'reports':
          return getReportDetail(selectedId, selectedMeta.report_type)
        case 'posts':
          return getPostDetail(selectedId)
        case 'users':
          return getUserDetail(selectedId)
        case 'returned':
          return getReturnedDetail(selectedId)
        case 'claims':
          return getClaimOverviewDetail(selectedId)
        default:
          return null
      }
    },
    enabled: enabled && !!selectedId && ['disputes', 'reports', 'posts', 'users', 'returned', 'claims'].includes(section),
  })

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['admin'] })
    detailQuery.refetch()
  }

  const openConfirm = (cfg) => setConfirm({ ...cfg, open: true })
  const closeConfirm = () => setConfirm(null)

  const roleLabel = useMemo(() => {
    if (user?.role === 'root_admin') return 'Root Admin'
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
      case 'disputes':
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
                description: 'Pauses further activity on this item until the dispute is resolved.',
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
                description: 'Their posts will be hidden from public browse per platform policy.',
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
            {u?.status === 'active' && u?.role === 'user' && (
              <button type="button" className="btn-secondary admin-btn-sm" onClick={() => openConfirm({
                title: 'Suspend user?',
                description: 'Posts will be hidden per Section 4.7.',
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
                description: 'Restores posts and account access.',
                onConfirm: async () => {
                  await unsuspendUser(selectedId); toast.success('Unsuspended'); refresh(); usersQuery.refetch()
                },
              })}>Unsuspend</button>
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
      case 'disputes':
        return (disputesQuery.data?.disputes || []).map((d) => (
          <button key={`${d.dispute_type}-${d.dispute_id}`} type="button" onClick={() => navigateToItem('disputes', d.dispute_id, { dispute_type: d.dispute_type })} className={queueItemClass(selectedId === d.dispute_id)}>
            <p className="text-xs text-brand-400 uppercase">{d.dispute_type}</p>
            <p className="text-sm">{d.item_label}</p>
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
              <span className="truncate"><span className="text-slate-400">Owner</span> @{r.owner_username}</span>
              <span className="truncate">
                <span className="text-slate-400">Finder</span>{' '}
                {r.finder_username ? `@${r.finder_username}` : (r.finder_name || 'Anonymous')}
              </span>
              <span><span className="text-slate-400">Lost</span> {formatDateShort(r.date_lost)}</span>
              <span><span className="text-slate-400">Found</span> {formatDateShort(r.date_found)}</span>
              <span className="col-span-2"><span className="text-slate-400">Returned</span> {formatDateShort(r.date_returned)}</span>
              {r.drop_point_name && (
                <span className="col-span-2"><span className="text-slate-400">Drop point</span> {r.drop_point_name}</span>
              )}
              {r.handover_completed && (
                <span className="col-span-2 text-emerald-500/90">
                  Handover complete{r.handover_authority_override ? ' (authority override)' : r.handover_owner_confirmed ? ' (owner confirmed)' : ''}
                </span>
              )}
            </div>
          </button>
        ))
      case 'claims': {
        const q = claimsFilter.trim().toLowerCase()
        return (claimsQuery.data?.items || [])
          .filter((item) => {
            if (!q) return true
            return item.drop_point_name.toLowerCase().includes(q)
              || item.found_item_description.toLowerCase().includes(q)
          })
          .map((item) => (
            <button
              key={item.found_item_id}
              type="button"
              onClick={() => navigateToItem('claims', item.found_item_id)}
              className={queueItemClass(selectedId === item.found_item_id)}
            >
              <div className="flex flex-wrap justify-between gap-2">
                <p className="text-sm font-medium truncate">{item.found_item_description}</p>
                <span className="text-xs text-brand-400 shrink-0">{item.drop_point_name}</span>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                {item.found_item_category.replace(/_/g, ' ')} · {item.found_item_status.replace(/_/g, ' ')}
              </p>
              <p className="text-xs text-slate-400 mt-0.5">
                {item.claim_count} claim{item.claim_count !== 1 ? 's' : ''}
                {' · '}{item.pending_count} pending
                {' · '}{item.verified_count} verified
                {' · '}{item.rejected_count} rejected
              </p>
            </button>
          ))
      }
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
      case 'disputes':
        return <DisputeDetail detail={detail} actions={actions} />
      case 'reports':
        return <ReportDetail detail={detail} actions={actions} />
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
      case 'claims':
        return <ClaimDetail detail={detail} />
      default:
        return null
    }
  }

  const hasSplit = ['disputes', 'reports', 'posts', 'returned', 'users', 'claims'].includes(section)

  const navItems = NAV.filter((n) => !n.rootOnly || isRoot)

  const queueQuery = {
    disputes: disputesQuery,
    reports: reportsQuery,
    posts: postsQuery,
    returned: returnedQuery,
    users: usersQuery,
    claims: claimsQuery,
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
            onClick={() => goSection(item.id)}
            className={`text-left px-3 py-2 rounded-lg text-sm transition-colors ${
              section === item.id ? 'bg-brand-600/20 text-brand-600 dark:text-brand-300' : 'text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
          >
            {item.label}
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
                {!searchQuery.data.users?.length && !searchQuery.data.items?.length && (
                  <p className="px-3 py-3 text-slate-500">No results</p>
                )}
              </div>
            )}
          </div>
          <span className="hidden md:inline text-[10px] px-2 py-0.5 rounded-md bg-brand-500/10 text-brand-600 dark:text-brand-300 font-medium whitespace-nowrap">
            {roleLabel}
          </span>
          <ThemeToggleButton className="shrink-0" />
          <AdminNotificationBell onNavigate={navigateToItem} enabled={enabled} />
          <button type="button" className="text-xs text-red-500 hover:text-red-400 px-1.5 shrink-0" onClick={() => logout()}>Logout</button>
        </header>

        <main className="flex-1 p-4 lg:p-6 overflow-hidden flex flex-col">
          {section === 'drop_points' && isRoot && (
            <div className="overflow-y-auto space-y-6 max-w-4xl">
              <div className="glass p-5 space-y-4">
                <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Create drop point</h2>
                <form
                  className="grid gap-3 sm:grid-cols-2"
                  onSubmit={async (e) => {
                    e.preventDefault()
                    if (!dropPointForm.university_id || !dropPointForm.name || !dropPointForm.latitude || !dropPointForm.longitude) {
                      return toast.error('University, name, and coordinates are required')
                    }
                    setCreatingDropPoint(true)
                    try {
                      await createAdminDropPoint({
                        university_id: dropPointForm.university_id,
                        name: dropPointForm.name.trim(),
                        type: dropPointForm.type,
                        latitude: Number(dropPointForm.latitude),
                        longitude: Number(dropPointForm.longitude),
                        operating_hours: dropPointForm.operating_hours,
                      })
                      toast.success('Drop point created')
                      setDropPointForm({
                        university_id: '', name: '', type: 'faculty', latitude: '', longitude: '',
                        operating_hours: 'Mon-Fri 08:00-17:00',
                      })
                      dropPointsQuery.refetch()
                    } catch (err) {
                      toast.error(err.response?.data?.detail || 'Could not create drop point')
                    } finally {
                      setCreatingDropPoint(false)
                    }
                  }}
                >
                  <select
                    className="admin-select sm:col-span-2"
                    value={dropPointForm.university_id}
                    onChange={(e) => setDropPointForm((f) => ({ ...f, university_id: e.target.value }))}
                  >
                    <option value="">Select university</option>
                    {(universitiesQuery.data || []).map((u) => (
                      <option key={u.id} value={u.id}>{u.short_name}</option>
                    ))}
                  </select>
                  <input className="admin-input-wide sm:col-span-2" placeholder="Name" value={dropPointForm.name} onChange={(e) => setDropPointForm((f) => ({ ...f, name: e.target.value }))} />
                  <select className="admin-select" value={dropPointForm.type} onChange={(e) => setDropPointForm((f) => ({ ...f, type: e.target.value }))}>
                    <option value="faculty">Faculty</option>
                    <option value="security">Security</option>
                  </select>
                  <input className="admin-input-wide" placeholder="Operating hours" value={dropPointForm.operating_hours} onChange={(e) => setDropPointForm((f) => ({ ...f, operating_hours: e.target.value }))} />
                  <input className="admin-input-wide" type="number" step="any" placeholder="Latitude" value={dropPointForm.latitude} onChange={(e) => setDropPointForm((f) => ({ ...f, latitude: e.target.value }))} />
                  <input className="admin-input-wide" type="number" step="any" placeholder="Longitude" value={dropPointForm.longitude} onChange={(e) => setDropPointForm((f) => ({ ...f, longitude: e.target.value }))} />
                  <button type="submit" className="btn-primary sm:col-span-2 admin-btn-sm" disabled={creatingDropPoint}>
                    {creatingDropPoint ? 'Creating…' : 'Create drop point'}
                  </button>
                </form>
              </div>

              <div className="glass p-5 space-y-3">
                <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                  All drop points ({dropPointsQuery.data?.drop_points?.length ?? '…'})
                </h2>
                {dropPointsQuery.isLoading && <QueueLoading label="drop points" />}
                {(dropPointsQuery.data?.drop_points || []).map((dp) => (
                  <div key={dp.id} className="border border-slate-700/50 rounded-lg p-3 text-sm space-y-2">
                    {editingDropPoint === dp.id ? (
                      <form
                        className="grid gap-2 sm:grid-cols-2"
                        onSubmit={async (e) => {
                          e.preventDefault()
                          try {
                            await updateAdminDropPoint(dp.id, {
                              name: dropPointEditForm.name,
                              type: dropPointEditForm.type,
                              latitude: Number(dropPointEditForm.latitude),
                              longitude: Number(dropPointEditForm.longitude),
                              operating_hours: dropPointEditForm.operating_hours,
                              is_temporarily_closed: dropPointEditForm.is_temporarily_closed,
                              closed_reason: dropPointEditForm.closed_reason || null,
                            })
                            toast.success('Drop point updated')
                            setEditingDropPoint(null)
                            dropPointsQuery.refetch()
                          } catch (err) {
                            toast.error(err.response?.data?.detail || 'Update failed')
                          }
                        }}
                      >
                        <input className="admin-input-wide sm:col-span-2" value={dropPointEditForm.name || ''} onChange={(e) => setDropPointEditForm((f) => ({ ...f, name: e.target.value }))} />
                        <select className="admin-select" value={dropPointEditForm.type || 'faculty'} onChange={(e) => setDropPointEditForm((f) => ({ ...f, type: e.target.value }))}>
                          <option value="faculty">Faculty</option>
                          <option value="security">Security</option>
                        </select>
                        <input className="admin-input-wide" value={dropPointEditForm.operating_hours || ''} onChange={(e) => setDropPointEditForm((f) => ({ ...f, operating_hours: e.target.value }))} />
                        <input className="admin-input-wide" type="number" step="any" value={dropPointEditForm.latitude ?? ''} onChange={(e) => setDropPointEditForm((f) => ({ ...f, latitude: e.target.value }))} />
                        <input className="admin-input-wide" type="number" step="any" value={dropPointEditForm.longitude ?? ''} onChange={(e) => setDropPointEditForm((f) => ({ ...f, longitude: e.target.value }))} />
                        <label className="flex items-center gap-2 text-xs sm:col-span-2">
                          <input type="checkbox" checked={Boolean(dropPointEditForm.is_temporarily_closed)} onChange={(e) => setDropPointEditForm((f) => ({ ...f, is_temporarily_closed: e.target.checked }))} />
                          Temporarily closed
                        </label>
                        {dropPointEditForm.is_temporarily_closed && (
                          <input className="admin-input-wide sm:col-span-2" placeholder="Closed reason" value={dropPointEditForm.closed_reason || ''} onChange={(e) => setDropPointEditForm((f) => ({ ...f, closed_reason: e.target.value }))} />
                        )}
                        <div className="flex gap-2 sm:col-span-2">
                          <button type="submit" className="btn-primary admin-btn-sm">Save</button>
                          <button type="button" className="btn-secondary admin-btn-sm" onClick={() => setEditingDropPoint(null)}>Cancel</button>
                        </div>
                      </form>
                    ) : (
                      <>
                        <div className="flex flex-wrap justify-between gap-2">
                          <div>
                            <p className="font-medium text-slate-800 dark:text-slate-200">{dp.name}</p>
                            <p className="text-xs text-slate-500">{dp.university_name} · {dp.type}</p>
                            <p className="text-xs text-slate-500">{dp.operating_hours}</p>
                            {dp.is_temporarily_closed && (
                              <p className="text-xs text-amber-400 mt-1">Closed: {dp.closed_reason || 'No reason given'}</p>
                            )}
                          </div>
                          <button
                            type="button"
                            className="btn-secondary admin-btn-sm text-xs"
                            onClick={() => {
                              setEditingDropPoint(dp.id)
                              setDropPointEditForm({
                                name: dp.name,
                                type: dp.type,
                                latitude: dp.latitude,
                                longitude: dp.longitude,
                                operating_hours: dp.operating_hours,
                                is_temporarily_closed: dp.is_temporarily_closed,
                                closed_reason: dp.closed_reason || '',
                              })
                            }}
                          >
                            Edit
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                ))}
                {!dropPointsQuery.isLoading && !(dropPointsQuery.data?.drop_points || []).length && (
                  <EmptyQueue section="drop_points" />
                )}
              </div>
            </div>
          )}

          {section === 'token_settings' && isRoot && (
            <div className="overflow-y-auto max-w-md">
              <div className="glass p-5 space-y-4">
                <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Token reward values</h2>
                <p className="text-xs text-slate-500">Changes apply to future awards only (Section 12.1).</p>
                {tokenSettingsQuery.isLoading && <QueueLoading label="token settings" />}
                {tokenSettingsForm && (
                  <form
                    className="space-y-3"
                    onSubmit={async (e) => {
                      e.preventDefault()
                      setSavingTokenSettings(true)
                      try {
                        await updateTokenSettings({
                          found_item_posted: Number(tokenSettingsForm.found_item_posted),
                          drop_off_on_time: Number(tokenSettingsForm.drop_off_on_time),
                          drop_off_late: Number(tokenSettingsForm.drop_off_late),
                          item_claimed: Number(tokenSettingsForm.item_claimed),
                        })
                        toast.success('Token settings saved')
                        tokenSettingsQuery.refetch()
                      } catch (err) {
                        toast.error(err.response?.data?.detail || 'Save failed')
                      } finally {
                        setSavingTokenSettings(false)
                      }
                    }}
                  >
                    {[
                      ['found_item_posted', 'Found item posted'],
                      ['drop_off_on_time', 'Drop-off on time'],
                      ['drop_off_late', 'Drop-off late'],
                      ['item_claimed', 'Item claimed'],
                    ].map(([key, label]) => (
                      <label key={key} className="block text-sm">
                        <span className="text-slate-500 text-xs">{label}</span>
                        <input
                          type="number"
                          min="0"
                          className="admin-input-wide mt-1"
                          value={tokenSettingsForm[key]}
                          onChange={(e) => setTokenSettingsForm((f) => ({ ...f, [key]: e.target.value }))}
                        />
                      </label>
                    ))}
                    <button type="submit" className="btn-primary admin-btn-sm" disabled={savingTokenSettings}>
                      {savingTokenSettings ? 'Saving…' : 'Save settings'}
                    </button>
                  </form>
                )}
              </div>
            </div>
          )}

          {section === 'redemption' && (
            <div className="overflow-y-auto max-w-xl">
              <div className="glass p-5 space-y-4">
                <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                  Redemption Lookup
                </h2>
                <p className="text-xs text-slate-500">
                  Enter a user&apos;s redemption code to verify its value and mark it as redeemed.
                  Each code is single-use.
                </p>
                <form
                  className="flex flex-col sm:flex-row gap-2"
                  onSubmit={async (e) => {
                    e.preventDefault()
                    const code = redemptionCode.trim()
                    if (!code) return toast.error('Enter a redemption code')
                    setRedemptionLoading(true)
                    try {
                      const data = await lookupRedemptionCode(code)
                      setRedemptionResult(data)
                      if (data.status === 'redeemed' && data.message.includes('successfully')) {
                        toast.success('Code redeemed')
                      } else if (data.status === 'redeemed') {
                        toast.error(data.message)
                      } else if (data.status === 'expired') {
                        toast.error(data.message)
                      }
                    } catch (err) {
                      setRedemptionResult(null)
                      toast.error(err.response?.data?.detail || 'Lookup failed')
                    } finally {
                      setRedemptionLoading(false)
                    }
                  }}
                >
                  <input
                    type="text"
                    className="admin-input-wide flex-1 font-mono uppercase"
                    placeholder="FAIND-XXXXXX"
                    value={redemptionCode}
                    onChange={(e) => setRedemptionCode(e.target.value.toUpperCase())}
                  />
                  <button
                    type="submit"
                    className="btn-primary admin-btn-sm shrink-0"
                    disabled={redemptionLoading}
                  >
                    {redemptionLoading ? 'Looking up…' : 'Look up & Redeem'}
                  </button>
                </form>

                {redemptionResult && (
                  <div className="rounded-lg border border-slate-200/60 dark:border-slate-700/50 p-4 space-y-2 text-sm">
                    <div className="flex justify-between gap-2">
                      <span className="text-slate-500">Code</span>
                      <span className="font-mono font-semibold text-slate-800 dark:text-slate-100">
                        {redemptionResult.code}
                      </span>
                    </div>
                    <div className="flex justify-between gap-2">
                      <span className="text-slate-500">Value</span>
                      <span className="font-semibold tabular-nums">
                        {redemptionResult.token_amount} tokens
                      </span>
                    </div>
                    <div className="flex justify-between gap-2">
                      <span className="text-slate-500">Status</span>
                      <span className={`font-medium capitalize ${
                        redemptionResult.status === 'redeemed'
                          ? 'text-green-500'
                          : redemptionResult.status === 'expired'
                            ? 'text-amber-500'
                            : 'text-slate-700 dark:text-slate-300'
                      }`}>
                        {redemptionResult.status}
                      </span>
                    </div>
                    <div className="flex justify-between gap-2">
                      <span className="text-slate-500">Owner</span>
                      <span className="text-slate-800 dark:text-slate-200 text-right">
                        {redemptionResult.owner.full_name}
                        <span className="text-slate-500"> @{redemptionResult.owner.username}</span>
                      </span>
                    </div>
                    <div className="flex justify-between gap-2">
                      <span className="text-slate-500">Expires</span>
                      <span>{formatDateShort(redemptionResult.expires_at)}</span>
                    </div>
                    {redemptionResult.redeemed_at && (
                      <div className="flex justify-between gap-2">
                        <span className="text-slate-500">Redeemed</span>
                        <span>{formatDateShort(redemptionResult.redeemed_at)}</span>
                      </div>
                    )}
                    <p className="text-xs text-slate-400 pt-2 border-t border-slate-700/40">
                      {redemptionResult.message}
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          {section === 'supervisors' && isRoot && (
            <div className="overflow-y-auto space-y-6 max-w-3xl">
              <div className="glass p-5 space-y-4">
                <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Create supervisor</h2>
                <p className="text-xs text-slate-500">
                  Assign one or more drop points. Supervisors manage authorities and view items/claims in scope.
                </p>
                <form
                  className="grid gap-3"
                  onSubmit={async (e) => {
                    e.preventDefault()
                    if (!supervisorForm.email || !supervisorForm.password || !supervisorForm.university_id) {
                      return toast.error('Email, password, and university are required')
                    }
                    setCreatingSupervisor(true)
                    try {
                      await createSupervisor({
                        email: supervisorForm.email.trim(),
                        password: supervisorForm.password,
                        university_id: supervisorForm.university_id,
                        drop_point_ids: supervisorForm.drop_point_ids,
                      })
                      toast.success('Supervisor created')
                      setSupervisorForm({ email: '', password: '', university_id: '', drop_point_ids: [] })
                      supervisorsQuery.refetch()
                    } catch (err) {
                      toast.error(err.response?.data?.detail || 'Could not create supervisor')
                    } finally {
                      setCreatingSupervisor(false)
                    }
                  }}
                >
                  <input
                    type="email"
                    className="admin-input-wide"
                    placeholder="supervisor@university.edu"
                    value={supervisorForm.email}
                    onChange={(e) => setSupervisorForm((f) => ({ ...f, email: e.target.value }))}
                  />
                  <input
                    type="password"
                    className="admin-input-wide"
                    placeholder="Password"
                    value={supervisorForm.password}
                    onChange={(e) => setSupervisorForm((f) => ({ ...f, password: e.target.value }))}
                  />
                  <select
                    className="admin-select admin-input-wide"
                    value={supervisorForm.university_id}
                    onChange={(e) => setSupervisorForm((f) => ({
                      ...f,
                      university_id: e.target.value,
                      drop_point_ids: [],
                    }))}
                  >
                    <option value="">Select university</option>
                    {(universitiesQuery.data || []).map((u) => (
                      <option key={u.id} value={u.id}>{u.short_name}</option>
                    ))}
                  </select>
                  {supervisorForm.university_id && (
                    <div className="space-y-2 max-h-40 overflow-y-auto border border-slate-700/50 rounded-lg p-3">
                      <p className="text-xs text-slate-500">Assigned drop points</p>
                      {(supervisorDropPointsQuery.data?.drop_points || []).map((dp) => (
                        <label key={dp.id} className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                          <input
                            type="checkbox"
                            checked={supervisorForm.drop_point_ids.includes(dp.id)}
                            onChange={(e) => {
                              setSupervisorForm((f) => ({
                                ...f,
                                drop_point_ids: e.target.checked
                                  ? [...f.drop_point_ids, dp.id]
                                  : f.drop_point_ids.filter((id) => id !== dp.id),
                              }))
                            }}
                          />
                          {dp.name}
                        </label>
                      ))}
                    </div>
                  )}
                  <button type="submit" className="btn-primary admin-btn-sm" disabled={creatingSupervisor}>
                    {creatingSupervisor ? 'Creating…' : 'Create supervisor'}
                  </button>
                </form>
              </div>

              <div className="glass p-5 space-y-3">
                <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Supervisors</h2>
                {!supervisorsQuery.data?.supervisors?.length ? (
                  <p className="text-sm text-slate-500">No supervisors yet.</p>
                ) : (
                  <ul className="space-y-3">
                    {supervisorsQuery.data.supervisors.map((s) => (
                      <li
                        key={s.id}
                        className="border border-slate-700/50 rounded-lg p-3 text-sm"
                      >
                        <div className="flex flex-wrap justify-between gap-2">
                          <div>
                            <p className="font-medium text-slate-800 dark:text-slate-200">{s.email}</p>
                            <p className="text-xs text-slate-500">
                              {s.drop_point_names.length
                                ? s.drop_point_names.join(', ')
                                : 'No drop points assigned'}
                            </p>
                          </div>
                          <button
                            type="button"
                            className="btn-secondary admin-btn-sm text-xs"
                            onClick={async () => {
                              try {
                                await updateSupervisor(s.id, { is_active: !s.is_active })
                                toast.success(s.is_active ? 'Deactivated' : 'Activated')
                                supervisorsQuery.refetch()
                              } catch (err) {
                                toast.error(err.response?.data?.detail || 'Failed')
                              }
                            }}
                          >
                            {s.is_active ? 'Deactivate' : 'Activate'}
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}

          {section === 'authorities' && isRoot && (
            <div className="overflow-y-auto space-y-6 max-w-3xl">
              <div className="glass p-5 space-y-4">
                <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Create authority account</h2>
                <p className="text-xs text-slate-500">One account per drop point. Email must be @gctu.edu.gh.</p>
                <form
                  className="grid gap-3 sm:grid-cols-2"
                  onSubmit={async (e) => {
                    e.preventDefault()
                    if (!authorityForm.email || !authorityForm.password || !authorityForm.drop_point_id) {
                      return toast.error('Fill in all fields')
                    }
                    setCreatingAuthority(true)
                    try {
                      await createAuthority({
                        email: authorityForm.email.trim(),
                        password: authorityForm.password,
                        drop_point_id: authorityForm.drop_point_id,
                      })
                      toast.success('Authority account created')
                      setAuthorityForm({ email: '', password: '', drop_point_id: '' })
                      authoritiesQuery.refetch()
                    } catch (err) {
                      toast.error(err.response?.data?.detail || 'Could not create authority')
                    } finally {
                      setCreatingAuthority(false)
                    }
                  }}
                >
                  <input
                    type="email"
                    className="admin-input-wide sm:col-span-2"
                    placeholder="authority@gctu.edu.gh"
                    value={authorityForm.email}
                    onChange={(e) => setAuthorityForm((f) => ({ ...f, email: e.target.value }))}
                  />
                  <input
                    type="password"
                    className="admin-input-wide"
                    placeholder="Temporary password (min 8 chars)"
                    value={authorityForm.password}
                    onChange={(e) => setAuthorityForm((f) => ({ ...f, password: e.target.value }))}
                  />
                  <select
                    className="admin-select"
                    value={authorityForm.drop_point_id}
                    onChange={(e) => setAuthorityForm((f) => ({ ...f, drop_point_id: e.target.value }))}
                  >
                    <option value="">Select drop point…</option>
                    {(authDropPointsQuery.data?.drop_points || []).map((dp) => (
                      <option key={dp.id} value={dp.id}>{dp.name}</option>
                    ))}
                  </select>
                  <button type="submit" className="btn-primary sm:col-span-2 text-sm" disabled={creatingAuthority}>
                    {creatingAuthority ? 'Creating…' : 'Create authority'}
                  </button>
                </form>
              </div>

              <div className="glass p-5">
                <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100 mb-3">Authority accounts</h2>
                {authoritiesQuery.isLoading && <QueueLoading label="authorities" />}
                {authoritiesQuery.isError && <QueueError message="Failed to load authorities." />}
                <div className="space-y-2">
                  {(authoritiesQuery.data?.authorities || []).map((auth) => (
                    <div key={auth.id} className="admin-queue-item flex flex-col gap-2">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div>
                          <p className="text-sm font-medium">{auth.email}</p>
                          <p className="text-xs text-slate-500">{auth.drop_point_name}</p>
                          <p className={`text-xs mt-0.5 ${auth.is_active ? 'text-emerald-600' : 'text-red-500'}`}>
                            {auth.is_active ? 'Active' : 'Deactivated'}
                          </p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <button
                            type="button"
                            className="btn-secondary admin-btn-sm text-xs"
                            onClick={() => {
                              setReassignAuthId(auth.id)
                              setReassignDropPointId('')
                            }}
                          >
                            Reassign
                          </button>
                          <button
                            type="button"
                            className="btn-secondary admin-btn-sm text-xs"
                            onClick={async () => {
                              try {
                                if (auth.is_active) {
                                  await deactivateAuthority(auth.id)
                                  toast.success('Authority deactivated')
                                } else {
                                  await activateAuthority(auth.id)
                                  toast.success('Authority activated')
                                }
                                authoritiesQuery.refetch()
                              } catch (err) {
                                toast.error(err.response?.data?.detail || 'Action failed')
                              }
                            }}
                          >
                            {auth.is_active ? 'Deactivate' : 'Activate'}
                          </button>
                        </div>
                      </div>
                      {reassignAuthId === auth.id && (
                        <div className="flex flex-wrap gap-2 items-center border-t border-slate-700/40 pt-2">
                          <select
                            className="admin-select flex-1 min-w-[180px]"
                            value={reassignDropPointId}
                            onChange={(e) => setReassignDropPointId(e.target.value)}
                          >
                            <option value="">Select new drop point…</option>
                            {(authDropPointsQuery.data?.drop_points || [])
                              .filter((dp) => dp.id !== auth.drop_point_id)
                              .map((dp) => (
                                <option key={dp.id} value={dp.id}>{dp.name}</option>
                              ))}
                          </select>
                          <button
                            type="button"
                            className="btn-primary admin-btn-sm text-xs"
                            disabled={!reassignDropPointId}
                            onClick={async () => {
                              try {
                                await reassignAuthority(auth.id, reassignDropPointId)
                                toast.success('Authority reassigned')
                                setReassignAuthId(null)
                                authoritiesQuery.refetch()
                              } catch (err) {
                                toast.error(err.response?.data?.detail || 'Reassign failed')
                              }
                            }}
                          >
                            Confirm
                          </button>
                          <button type="button" className="btn-secondary admin-btn-sm text-xs" onClick={() => setReassignAuthId(null)}>Cancel</button>
                        </div>
                      )}
                    </div>
                  ))}
                  {!authoritiesQuery.isLoading && !(authoritiesQuery.data?.authorities || []).length && (
                    <p className="text-sm text-slate-500 py-4 text-center">No authority accounts yet.</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {section === 'settings' && (
            <div className="max-w-lg">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">Admin settings</h2>
              <div className="glass p-6 border border-slate-800">
                <StaffPushSettingsToggle role="admin" />
              </div>
            </div>
          )}

          {section === 'overview' && (
            analyticsQuery.isLoading ? <QueueLoading label="analytics" />
              : analyticsQuery.isError ? <QueueError message="Failed to load analytics." />
              : a && (
            <div className="overflow-y-auto space-y-4">
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-2">
                <StatCard label="Found items posted" value={a.total_found_items} />
                <StatCard label="Drop-off rate" value={`${a.drop_off_rate_percent}%`} />
                <StatCard label="Avg hrs to drop-off" value={a.avg_hours_to_drop_off ?? '—'} />
                <StatCard label="Avg hrs to claim" value={a.avg_hours_to_claim ?? '—'} />
                <StatCard label="Tokens issued" value={a.tokens_total_issued} />
                <StatCard label="Tokens redeemed" value={a.tokens_total_redeemed} />
                <StatCard label="Returned (all)" value={a.total_returned} />
                <StatCard label="Return rate" value={`${a.return_rate_percent}%`} />
                <StatCard label="Found this week" value={a.found_items_this_week} />
                <StatCard label="Returned this week" value={a.returned_this_week} />
                <StatCard label="Claims pending" value={a.claims_pending_review} onClick={() => goSection('claims')} />
                <StatCard label="Open disputes" value={a.disputes_open} highlight="amber" onClick={() => goSection('disputes')} />
                <StatCard label="Pending reports" value={a.reports_pending} highlight="amber" onClick={() => goSection('reports')} />
              </div>
              {a.items_per_drop_point?.length > 0 && (
                <div className="glass p-4">
                  <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100 mb-3">Found items per drop point</h2>
                  <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
                    {a.items_per_drop_point.map((dp) => (
                      <div key={dp.drop_point_id} className="admin-stat">
                        <p className="text-[10px] text-slate-500 uppercase tracking-wide line-clamp-2">{dp.drop_point_name}</p>
                        <p className="text-lg font-bold tabular-nums mt-1">{dp.found_item_count}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}

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
              </select>
              {returnedQuery.data?.total != null && (
                <span className="text-[10px] text-slate-500 whitespace-nowrap">{returnedQuery.data.total} returned</span>
              )}
            </div>
          )}

          {section === 'claims' && hasSplit && isRoot && (
            <div className="admin-toolbar">
              <input
                className="admin-input-wide"
                placeholder="Filter by drop point or description…"
                value={claimsFilter}
                onChange={(e) => setClaimsFilter(e.target.value)}
              />
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
                      <p className="text-slate-700 dark:text-slate-300">
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

      <AdminPushPromptTrigger />
      <StaffPushPromptBanner role="admin" enabled={isAdminRole(user?.role)} />
    </div>
  )
}
