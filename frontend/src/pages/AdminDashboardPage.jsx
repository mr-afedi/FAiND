/**
 * Admin Dashboard — Feature R (Section 26) with detail panels & notifications.
 */
import { useState, useEffect, useCallback } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useAuth } from '../context/AuthContext'
import AdminNotificationBell from '../components/AdminNotificationBell'
import AdminDetailPanel, {
  ClaimDetail,
  DisputeDetail,
  ReportDetail,
  FraudDetail,
  PostDetail,
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
  isValidAdminSecret,
  rememberAdminSecret,
  isAdminRole,
} from '../services/adminService'

const NAV = [
  { id: 'overview', label: 'Overview' },
  { id: 'users', label: 'Users' },
  { id: 'claims', label: 'Claims Review' },
  { id: 'disputes', label: 'Disputes' },
  { id: 'reports', label: 'Reports' },
  { id: 'fraud', label: 'Fraud Alerts' },
  { id: 'posts', label: 'Posts' },
  { id: 'logs', label: 'Admin Logs', rootOnly: true },
]

function StatCard({ label, value }) {
  return (
    <div className="glass p-4">
      <p className="text-xs text-slate-500 uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-bold text-slate-800 dark:text-slate-100 mt-1">{value}</p>
    </div>
  )
}

export default function AdminDashboardPage() {
  const { adminSecret } = useParams()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { user, loading: authLoading, logout, isAuthenticated } = useAuth()
  const queryClient = useQueryClient()

  const [section, setSection] = useState(searchParams.get('section') || 'overview')
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
    queryKey: ['admin-users', userSearch],
    queryFn: () => listUsers({ search: userSearch || undefined }),
    enabled: section === 'users' && enabled,
  })

  const claimsQuery = useQuery({
    queryKey: ['admin-claims'],
    queryFn: listClaims,
    enabled: section === 'claims' && enabled,
  })

  const disputesQuery = useQuery({
    queryKey: ['admin-disputes'],
    queryFn: listDisputes,
    enabled: section === 'disputes' && enabled,
  })

  const reportsQuery = useQuery({
    queryKey: ['admin-reports'],
    queryFn: () => listReports('pending'),
    enabled: section === 'reports' && enabled,
  })

  const fraudQuery = useQuery({
    queryKey: ['admin-fraud'],
    queryFn: listFraudAlerts,
    enabled: section === 'fraud' && enabled,
  })

  const postsQuery = useQuery({
    queryKey: ['admin-posts', postSearch],
    queryFn: () => listPostsModeration({
      search: postSearch || undefined,
      limit: 100,
    }),
    enabled: section === 'posts' && enabled,
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
        default:
          return null
      }
    },
    enabled: enabled && !!selectedId && ['claims', 'disputes', 'reports', 'fraud', 'posts', 'users'].includes(section),
  })

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['admin'] })
    detailQuery.refetch()
  }

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
    <div className="flex flex-wrap gap-2 mt-4 pt-3 border-t border-slate-800">{buttons}</div>
  )

  const renderDetailActions = () => {
    if (!selectedId) return null
    switch (section) {
      case 'claims':
        return actionBtns(
          <>
            <button type="button" className="btn-primary text-xs py-1.5" onClick={() => approveClaimMut.mutate(selectedId)}>Approve</button>
            <button type="button" className="btn-secondary text-xs py-1.5" onClick={async () => {
              try {
                await rejectClaim(selectedId, actionNote || 'Rejected by admin')
                toast.success('Rejected'); refresh(); claimsQuery.refetch()
              } catch (e) { toast.error(e.response?.data?.detail || 'Failed') }
            }}>Reject</button>
            <button type="button" className="btn-secondary text-xs py-1.5" disabled={actionNote.trim().length < 10} onClick={async () => {
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
                className="input-field text-xs py-1 min-w-[180px]"
                value={winnerMatchId}
                onChange={(e) => setWinnerMatchId(e.target.value)}
              >
                <option value="">Select winning claimant…</option>
                {claimants.map((c) => (
                  <option key={c.match_id} value={c.match_id}>
                    {c.claimant?.full_name || 'Unknown'} — {c.path} (score {c.match_score})
                  </option>
                ))}
              </select>
              <textarea className="input-field text-xs flex-1 min-w-[200px]" rows={2} placeholder="Resolution note (min 10 chars)" value={actionNote} onChange={(e) => setActionNote(e.target.value)} />
              <button
                type="button"
                className="btn-primary text-xs py-1.5"
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
            <select className="input-field text-xs py-1" value={disputeOutcome} onChange={(e) => setDisputeOutcome(e.target.value)}>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="more_info">More info</option>
              <option value="flagged">Flagged</option>
            </select>
            <textarea className="input-field text-xs flex-1 min-w-[200px]" rows={2} placeholder="Note (min 10 chars)" value={actionNote} onChange={(e) => setActionNote(e.target.value)} />
            <button type="button" className="btn-primary text-xs py-1.5" disabled={actionNote.trim().length < 10} onClick={async () => {
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
              <button type="button" className="btn-secondary text-xs py-1.5" onClick={async () => { await dismissPostReport(selectedId); toast.success('Dismissed'); refresh(); reportsQuery.refetch() }}>Dismiss</button>
              <button type="button" className="btn-primary text-xs py-1.5" onClick={async () => { await removeReportedPost(selectedId); toast.success('Post removed'); refresh(); reportsQuery.refetch() }}>Remove post</button>
              <button type="button" className="btn-secondary text-xs py-1.5" onClick={async () => {
                const reporterId = detail?.report?.reporter?.id
                if (!reporterId) return
                await suppressReporter(reporterId)
                toast.success('Reporter marked bad faith')
              }}>Mark reporter bad faith</button>
            </>
          ) : (
            <>
              <button type="button" className="btn-secondary text-xs py-1.5" onClick={async () => { await dismissUserReport(selectedId); toast.success('Dismissed'); refresh(); reportsQuery.refetch() }}>Dismiss</button>
              <button type="button" className="btn-secondary text-xs py-1.5" onClick={async () => { await warnUserReport(selectedId); toast.success('Warned'); refresh(); reportsQuery.refetch() }}>Warn user</button>
              <button type="button" className="btn-primary text-xs py-1.5" onClick={async () => {
                if (!window.confirm('Suspend this user? Their posts will be hidden and chats frozen.')) return
                await suspendUserReport(selectedId); toast.success('Suspended'); refresh(); reportsQuery.refetch()
              }}>Suspend user</button>
              <button type="button" className="btn-secondary text-xs py-1.5" onClick={async () => {
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
              <button type="button" className="btn-primary text-xs py-1.5" onClick={async () => {
                try { await confirmFraud(selectedId); toast.success('Fraud confirmed'); refresh(); fraudQuery.refetch() }
                catch (e) { toast.error(e.response?.data?.detail || 'Failed') }
              }}>Confirm fraud</button>
            )}
            <button type="button" className="btn-secondary text-xs py-1.5" onClick={async () => {
              try { await clearFraudFlag(selectedId); toast.success('Flag cleared'); refresh(); fraudQuery.refetch() }
              catch (e) { toast.error(e.response?.data?.detail || 'Failed') }
            }}>Clear flag</button>
            <button type="button" className="btn-secondary text-xs py-1.5" onClick={async () => {
              if (!window.confirm('Suspend this user? Their posts will be hidden and chats frozen.')) return
              try { await suspendUser(selectedId, 'Fraud review suspension'); toast.success('Suspended'); refresh() }
              catch (e) { toast.error(e.response?.data?.detail || 'Failed') }
            }}>Suspend user</button>
            <button type="button" className="btn-secondary text-xs py-1.5" onClick={async () => {
              try { await allowVerification(selectedId); toast.success('Verification allowed'); refresh() }
              catch (e) { toast.error(e.response?.data?.detail || 'Failed') }
            }}>Allow verification</button>
          </>,
        )
      case 'posts':
        return actionBtns(
          <>
            <button type="button" className="btn-secondary text-xs py-1.5" onClick={async () => {
              try { await removePost(selectedId, 'Admin removal'); toast.success('Removed'); refresh(); postsQuery.refetch() }
              catch (e) { toast.error(e.response?.data?.detail || 'Failed') }
            }}>Remove post</button>
            <button type="button" className="btn-primary text-xs py-1.5" onClick={async () => {
              try { await forceClosePost(selectedId, 'Admin force close'); toast.success('Force closed'); refresh(); postsQuery.refetch() }
              catch (e) { toast.error(e.response?.data?.detail || 'Failed') }
            }}>Force close</button>
          </>,
        )
      case 'users': {
        const u = usersQuery.data?.users?.find((x) => x.id === selectedId) || detail?.profile
        return actionBtns(
          <>
            {u?.status === 'active' && u?.role === 'user' && (
              <button type="button" className="btn-secondary text-xs py-1.5" onClick={async () => {
                if (!window.confirm('Suspend this user? Their posts will be hidden and chats frozen.')) return
                await suspendUser(selectedId, 'Admin suspension'); toast.success('Suspended'); refresh(); usersQuery.refetch()
              }}>Suspend</button>
            )}
            {u?.status === 'suspended' && (
              <button type="button" className="btn-secondary text-xs py-1.5" onClick={async () => {
                if (!window.confirm('Lift suspension and restore this user\'s posts and chats?')) return
                await unsuspendUser(selectedId); toast.success('Unsuspended'); refresh(); usersQuery.refetch()
              }}>Unsuspend</button>
            )}
            {isRoot && u?.role === 'user' && (
              <button type="button" className="btn-primary text-xs py-1.5" onClick={async () => {
                await promoteAdmin(selectedId); toast.success('Promoted'); usersQuery.refetch()
              }}>Promote</button>
            )}
            {isRoot && u?.role === 'assistant_root_admin' && (
              <button type="button" className="btn-secondary text-xs py-1.5" onClick={async () => {
                await demoteAdmin(selectedId); toast.success('Demoted'); usersQuery.refetch()
              }}>Demote</button>
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
          <button key={c.match_id} type="button" onClick={() => navigateToItem('claims', c.match_id)} className={`w-full text-left glass p-3 ${selectedId === c.match_id ? 'ring-1 ring-brand-500' : ''}`}>
            <p className="text-xs text-brand-400 uppercase">{c.path}</p>
            <p className="text-sm">{c.claimant_name}</p>
            <p className="text-xs text-slate-500 truncate">Score {c.match_score}</p>
          </button>
        ))
      case 'disputes':
        return (disputesQuery.data?.disputes || []).map((d) => (
          <button key={`${d.dispute_type}-${d.dispute_id}`} type="button" onClick={() => navigateToItem('disputes', d.dispute_id, { dispute_type: d.dispute_type })} className={`w-full text-left glass p-3 ${selectedId === d.dispute_id ? 'ring-1 ring-brand-500' : ''}`}>
            <p className="text-xs text-brand-400 uppercase">{d.dispute_type}</p>
            <p className="text-sm">{d.item_label}</p>
            {d.tip_frozen && <p className="text-xs text-amber-400">Tip frozen</p>}
          </button>
        ))
      case 'reports':
        return (reportsQuery.data?.reports || []).map((r) => (
          <button key={r.id} type="button" onClick={() => navigateToItem('reports', r.id, { report_type: r.report_type })} className={`w-full text-left glass p-3 ${selectedId === r.id ? 'ring-1 ring-brand-500' : ''}`}>
            <p className="text-xs text-brand-400">{r.report_type} · {r.reason}</p>
            {r.auto_escalated && <span className="text-xs text-amber-400">Escalated</span>}
            <p className="text-sm truncate">{r.target_item_description || r.target_user_display_name}</p>
          </button>
        ))
      case 'fraud':
        return (fraudQuery.data?.alerts || []).map((u) => (
          <button key={u.user_id} type="button" onClick={() => navigateToItem('fraud', u.user_id)} className={`w-full text-left glass p-3 ${selectedId === u.user_id ? 'ring-1 ring-brand-500' : ''}`}>
            <p className="text-sm">{u.email}</p>
            <p className="text-xs text-slate-400">Risk {u.fraud_risk_score} ({u.risk_tier})</p>
          </button>
        ))
      case 'posts':
        return (postsQuery.data?.posts || []).map((p) => (
          <button key={p.item_id} type="button" onClick={() => navigateToItem('posts', p.item_id)} className={`w-full text-left glass p-3 ${selectedId === p.item_id ? 'ring-1 ring-brand-500' : ''}`}>
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
          <button key={u.id} type="button" onClick={() => navigateToItem('users', u.id)} className={`w-full text-left glass p-3 ${selectedId === u.id ? 'ring-1 ring-brand-500' : ''}`}>
            <p className="text-sm">{u.full_name}</p>
            <p className="text-xs text-slate-400">{u.email}</p>
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
        return <ClaimDetail detail={detail} actions={<>{actions}<textarea className="input-field w-full mt-2 text-xs" rows={2} placeholder="Note for reject / request info (min 10 chars)" value={actionNote} onChange={(e) => setActionNote(e.target.value)} /></>} />
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
      default:
        return null
    }
  }

  const hasSplit = ['claims', 'disputes', 'reports', 'fraud', 'posts', 'users'].includes(section)

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 flex">
      <aside className="w-56 border-r border-slate-800 p-4 flex flex-col gap-1 shrink-0">
        <p className="text-xs font-semibold text-brand-400 mb-3 px-2">FAiND Admin</p>
        {NAV.filter((n) => !n.rootOnly || isRoot).map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => { setSection(item.id); setSelectedId(null); setSearchParams({ section: item.id }) }}
            className={`text-left px-3 py-2 rounded-lg text-sm transition-colors ${
              section === item.id ? 'bg-brand-600/20 text-brand-300' : 'text-slate-400 hover:bg-slate-800'
            }`}
          >
            {item.label}
          </button>
        ))}
        <div className="mt-auto pt-4 border-t border-slate-800 space-y-2">
          <p className="text-xs text-slate-500 px-2 truncate">{user?.email}</p>
          <Link to="/" className="block text-xs text-slate-500 hover:text-slate-300 px-2">← Main site</Link>
          <button type="button" className="text-xs text-red-400 hover:text-red-300 px-2" onClick={() => logout()}>Logout</button>
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-h-screen">
        <header className="border-b border-slate-800 px-6 py-3 flex items-center justify-between shrink-0">
          <h1 className="text-lg font-bold capitalize">{section.replace('_', ' ')}</h1>
          <AdminNotificationBell onNavigate={navigateToItem} />
        </header>

        <main className="flex-1 p-6 overflow-hidden flex flex-col">
          {section === 'overview' && a && (
            <div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
                <StatCard label="Lost items" value={a.total_lost_items} />
                <StatCard label="Found items" value={a.total_found_items} />
                <StatCard label="Returned" value={a.total_returned} />
                <StatCard label="Return rate" value={`${a.return_rate_percent}%`} />
                <StatCard label="Claims in review" value={a.claims_pending_review} />
                <StatCard label="Open disputes" value={a.disputes_open} />
                <StatCard label="Pending reports" value={a.reports_pending} />
                <StatCard label="Fraud alerts" value={a.fraud_alerts} />
              </div>
              <p className="text-sm text-slate-400">Active posters (7d / 30d): {a.active_users_7d} / {a.active_users_30d}</p>
            </div>
          )}

          {section === 'users' && (
            <input className="input-field mb-4 max-w-md" placeholder="Search email, username…" value={userSearch} onChange={(e) => setUserSearch(e.target.value)} />
          )}

          {section === 'posts' && (
            <div className="mb-4 flex flex-wrap items-center gap-3">
              <input
                className="input-field max-w-md"
                placeholder="Search post descriptions…"
                value={postSearch}
                onChange={(e) => setPostSearch(e.target.value)}
              />
              {postsQuery.data?.total != null && (
                <p className="text-xs text-slate-500">{postsQuery.data.total} active post{postsQuery.data.total !== 1 ? 's' : ''}</p>
              )}
            </div>
          )}

          {section === 'logs' && isRoot && (
            <div className="space-y-3">
              <div className="flex gap-2 flex-wrap">
                <input className="input-field text-xs max-w-xs" placeholder="Filter by action type" value={logFilters.action} onChange={(e) => setLogFilters((f) => ({ ...f, action: e.target.value }))} />
                <input className="input-field text-xs max-w-xs" placeholder="Filter by admin UUID" value={logFilters.admin_id} onChange={(e) => setLogFilters((f) => ({ ...f, admin_id: e.target.value }))} />
              </div>
              <div className="space-y-2 text-sm max-h-[70vh] overflow-y-auto">
                {(logsQuery.data?.logs || []).map((log) => (
                  <div key={log.id} className="glass p-3">
                    <p className="text-slate-300"><span className="text-brand-400">{log.action}</span> · {log.admin_email || 'system'}</p>
                    <p className="text-xs text-slate-500">{log.target_type} {log.target_id} · {new Date(log.created_at).toLocaleString()}</p>
                    {Object.keys(log.detail || {}).length > 0 && (
                      <pre className="text-xs text-slate-600 mt-1">{JSON.stringify(log.detail)}</pre>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {hasSplit && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 flex-1 min-h-0">
              <div className="space-y-2 overflow-y-auto max-h-[calc(100vh-10rem)]">
                {section === 'posts' && postsQuery.isLoading && (
                  <p className="text-slate-500 text-sm">Loading posts…</p>
                )}
                {section === 'posts' && postsQuery.isError && (
                  <p className="text-red-400 text-sm">
                    Failed to load posts: {postsQuery.error?.response?.data?.detail || postsQuery.error?.message}
                  </p>
                )}
                {listItems}
                {!postsQuery.isLoading && listItems.length === 0 && (
                  <p className="text-slate-500 text-sm">
                    {section === 'posts'
                      ? (postSearch ? 'No posts match your search.' : 'No active posts on campus.')
                      : 'Queue empty.'}
                  </p>
                )}
              </div>
              <AdminDetailPanel section={section} detail={selectedId ? detail : null} loading={detailQuery.isLoading}>
                {renderDetailContent()}
              </AdminDetailPanel>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
