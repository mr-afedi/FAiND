/**
 * Admin Dashboard — Feature R (Section 26).
 */
import { useState, useEffect } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useAuth } from '../context/AuthContext'
import {
  adminGate,
  getAnalytics,
  listUsers,
  suspendUser,
  unsuspendUser,
  listClaims,
  approveClaim,
  rejectClaim,
  listDisputes,
  resolveDispute,
  listReports,
  dismissPostReport,
  removeReportedPost,
  dismissUserReport,
  warnUserReport,
  suspendUserReport,
  listFraudAlerts,
  confirmFraud,
  listPostsModeration,
  forceClosePost,
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
  const { user, loading: authLoading, logout, isAuthenticated } = useAuth()
  const queryClient = useQueryClient()
  const [section, setSection] = useState('overview')
  const [userSearch, setUserSearch] = useState('')
  const [disputeNote, setDisputeNote] = useState('')
  const [disputeOutcome, setDisputeOutcome] = useState('approved')
  const [selectedDispute, setSelectedDispute] = useState(null)

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

  const gateQuery = useQuery({
    queryKey: ['admin-gate'],
    queryFn: adminGate,
    enabled: isAuthenticated && isAdminRole(user?.role),
    retry: false,
  })

  const analyticsQuery = useQuery({
    queryKey: ['admin-analytics'],
    queryFn: getAnalytics,
    enabled: section === 'overview' && gateQuery.isSuccess,
  })

  const usersQuery = useQuery({
    queryKey: ['admin-users', userSearch],
    queryFn: () => listUsers({ search: userSearch || undefined }),
    enabled: section === 'users' && gateQuery.isSuccess,
  })

  const claimsQuery = useQuery({
    queryKey: ['admin-claims'],
    queryFn: listClaims,
    enabled: section === 'claims' && gateQuery.isSuccess,
  })

  const disputesQuery = useQuery({
    queryKey: ['admin-disputes'],
    queryFn: listDisputes,
    enabled: section === 'disputes' && gateQuery.isSuccess,
  })

  const reportsQuery = useQuery({
    queryKey: ['admin-reports'],
    queryFn: () => listReports('pending'),
    enabled: section === 'reports' && gateQuery.isSuccess,
  })

  const fraudQuery = useQuery({
    queryKey: ['admin-fraud'],
    queryFn: listFraudAlerts,
    enabled: section === 'fraud' && gateQuery.isSuccess,
  })

  const postsQuery = useQuery({
    queryKey: ['admin-posts'],
    queryFn: listPostsModeration,
    enabled: section === 'posts' && gateQuery.isSuccess,
  })

  const logsQuery = useQuery({
    queryKey: ['admin-logs'],
    queryFn: listAdminLogs,
    enabled: section === 'logs' && gateQuery.isSuccess && user?.role === 'root_admin',
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['admin'] })

  const approveClaimMut = useMutation({
    mutationFn: approveClaim,
    onSuccess: (d) => { toast.success(d.message); invalidate(); claimsQuery.refetch() },
    onError: (e) => toast.error(e.response?.data?.detail || 'Failed'),
  })

  const rejectClaimMut = useMutation({
    mutationFn: (id) => rejectClaim(id, 'Rejected by admin'),
    onSuccess: (d) => { toast.success(d.message); claimsQuery.refetch() },
    onError: (e) => toast.error(e.response?.data?.detail || 'Failed'),
  })

  const resolveDisputeMut = useMutation({
    mutationFn: ({ id, outcome, note }) => resolveDispute(id, outcome, note),
    onSuccess: (d) => {
      toast.success(d.message)
      setSelectedDispute(null)
      setDisputeNote('')
      disputesQuery.refetch()
    },
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

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 flex">
      <aside className="w-56 border-r border-slate-800 p-4 flex flex-col gap-1 shrink-0">
        <p className="text-xs font-semibold text-brand-400 mb-3 px-2">FAiND Admin</p>
        {NAV.filter((n) => !n.rootOnly || isRoot).map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setSection(item.id)}
            className={`text-left px-3 py-2 rounded-lg text-sm transition-colors ${
              section === item.id
                ? 'bg-brand-600/20 text-brand-300'
                : 'text-slate-400 hover:bg-slate-800'
            }`}
          >
            {item.label}
          </button>
        ))}
        <div className="mt-auto pt-4 border-t border-slate-800 space-y-2">
          <p className="text-xs text-slate-500 px-2 truncate">{user?.email}</p>
          <Link to="/" className="block text-xs text-slate-500 hover:text-slate-300 px-2">
            ← Main site
          </Link>
          <button
            type="button"
            className="text-xs text-red-400 hover:text-red-300 px-2"
            onClick={() => logout()}
          >
            Logout
          </button>
        </div>
      </aside>

      <main className="flex-1 p-6 overflow-y-auto max-h-screen">
        {section === 'overview' && a && (
          <div>
            <h1 className="text-xl font-bold mb-4">Platform analytics</h1>
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
            <p className="text-sm text-slate-400">
              Active posters (7d / 30d): {a.active_users_7d} / {a.active_users_30d}
            </p>
          </div>
        )}

        {section === 'users' && (
          <div>
            <h1 className="text-xl font-bold mb-4">User management</h1>
            <input
              className="input-field mb-4 max-w-md"
              placeholder="Search email, username…"
              value={userSearch}
              onChange={(e) => setUserSearch(e.target.value)}
            />
            <div className="space-y-2">
              {(usersQuery.data?.users || []).map((u) => (
                <div key={u.id} className="glass p-4 flex flex-wrap gap-3 items-center justify-between">
                  <div>
                    <p className="font-medium">{u.full_name}</p>
                    <p className="text-xs text-slate-400">{u.email} · {u.role} · {u.status}</p>
                    <p className="text-xs text-slate-500">
                      Trust {u.trust_score} · Fraud risk {u.fraud_risk_score}
                    </p>
                  </div>
                  <div className="flex gap-2 flex-wrap">
                    {u.status === 'active' && u.role === 'user' && (
                      <button
                        type="button"
                        className="btn-secondary text-xs py-1.5"
                        onClick={async () => {
                          try {
                            await suspendUser(u.id, 'Admin suspension')
                            toast.success('Suspended')
                            usersQuery.refetch()
                          } catch (e) {
                            toast.error(e.response?.data?.detail || 'Failed')
                          }
                        }}
                      >
                        Suspend
                      </button>
                    )}
                    {u.status === 'suspended' && (
                      <button
                        type="button"
                        className="btn-secondary text-xs py-1.5"
                        onClick={async () => {
                          try {
                            await unsuspendUser(u.id)
                            toast.success('Unsuspended')
                            usersQuery.refetch()
                          } catch (e) {
                            toast.error(e.response?.data?.detail || 'Failed')
                          }
                        }}
                      >
                        Unsuspend
                      </button>
                    )}
                    {isRoot && u.role === 'user' && (
                      <button
                        type="button"
                        className="btn-primary text-xs py-1.5"
                        onClick={async () => {
                          try {
                            await promoteAdmin(u.id)
                            toast.success('Promoted')
                            usersQuery.refetch()
                          } catch (e) {
                            toast.error(e.response?.data?.detail || 'Failed')
                          }
                        }}
                      >
                        Promote
                      </button>
                    )}
                    {isRoot && u.role === 'assistant_root_admin' && (
                      <button
                        type="button"
                        className="btn-secondary text-xs py-1.5"
                        onClick={async () => {
                          try {
                            await demoteAdmin(u.id)
                            toast.success('Demoted')
                            usersQuery.refetch()
                          } catch (e) {
                            toast.error(e.response?.data?.detail || 'Failed')
                          }
                        }}
                      >
                        Demote
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {section === 'claims' && (
          <div>
            <h1 className="text-xl font-bold mb-4">Claims review (0.50–0.75)</h1>
            <div className="space-y-3">
              {(claimsQuery.data?.claims || []).map((c) => (
                <div key={c.match_id} className="glass p-4">
                  <p className="text-xs text-brand-400 uppercase">{c.path}</p>
                  <p className="text-sm mt-1">{c.claimant_name}</p>
                  <p className="text-xs text-slate-400 mt-2">Lost: {c.lost_description}</p>
                  <p className="text-xs text-slate-400">Found: {c.found_description}</p>
                  <p className="text-xs text-slate-500 mt-1">Match score: {c.match_score}</p>
                  <div className="flex gap-2 mt-3">
                    <button
                      type="button"
                      className="btn-primary text-xs py-1.5"
                      onClick={() => approveClaimMut.mutate(c.match_id)}
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      className="btn-secondary text-xs py-1.5"
                      onClick={() => rejectClaimMut.mutate(c.match_id)}
                    >
                      Reject
                    </button>
                  </div>
                </div>
              ))}
              {!claimsQuery.data?.claims?.length && (
                <p className="text-slate-500 text-sm">No claims awaiting review.</p>
              )}
            </div>
          </div>
        )}

        {section === 'disputes' && (
          <div>
            <h1 className="text-xl font-bold mb-4">Open disputes</h1>
            <div className="space-y-3">
              {(disputesQuery.data?.disputes || []).map((d) => (
                <div key={d.return_id} className="glass p-4">
                  <p className="font-medium">{d.item_label}</p>
                  <p className="text-xs text-slate-400 mt-1">{d.dispute_reason}</p>
                  <p className="text-xs text-slate-500">
                    Filed by {d.filed_by_name} · {new Date(d.dispute_filed_at).toLocaleString()}
                  </p>
                  {d.tip_frozen && (
                    <p className="text-xs text-amber-400 mt-1">Tip frozen</p>
                  )}
                  <button
                    type="button"
                    className="btn-primary text-xs py-1.5 mt-3"
                    onClick={() => setSelectedDispute(d)}
                  >
                    Resolve
                  </button>
                </div>
              ))}
            </div>
            {selectedDispute && (
              <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60">
                <div className="glass max-w-md w-full p-6">
                  <h2 className="font-semibold mb-3">Resolve dispute</h2>
                  <select
                    className="input-field w-full mb-3"
                    value={disputeOutcome}
                    onChange={(e) => setDisputeOutcome(e.target.value)}
                  >
                    <option value="approved">Approved</option>
                    <option value="rejected">Rejected</option>
                    <option value="more_info">More information</option>
                    <option value="flagged">Flagged</option>
                  </select>
                  <textarea
                    className="input-field w-full mb-3"
                    rows={4}
                    placeholder="Resolution note (min 10 chars)…"
                    value={disputeNote}
                    onChange={(e) => setDisputeNote(e.target.value)}
                  />
                  <div className="flex gap-2">
                    <button type="button" className="btn-secondary flex-1" onClick={() => setSelectedDispute(null)}>
                      Cancel
                    </button>
                    <button
                      type="button"
                      className="btn-primary flex-1"
                      disabled={disputeNote.trim().length < 10}
                      onClick={() => resolveDisputeMut.mutate({
                        id: selectedDispute.return_id,
                        outcome: disputeOutcome,
                        note: disputeNote.trim(),
                      })}
                    >
                      Submit
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {section === 'reports' && (
          <div>
            <h1 className="text-xl font-bold mb-4">Reports queue</h1>
            <div className="space-y-3">
              {(reportsQuery.data?.reports || []).map((r) => (
                <div key={r.id} className="glass p-4">
                  <p className="text-xs text-brand-400">{r.report_type} · {r.reason}</p>
                  {r.auto_escalated && (
                    <span className="text-xs text-amber-400">Escalated</span>
                  )}
                  <p className="text-sm mt-1">
                    {r.target_item_description || r.target_user_display_name}
                  </p>
                  <div className="flex flex-wrap gap-2 mt-3">
                    {r.report_type === 'post' && (
                      <>
                        <button
                          type="button"
                          className="btn-secondary text-xs py-1.5"
                          onClick={async () => {
                            await dismissPostReport(r.id)
                            toast.success('Dismissed')
                            reportsQuery.refetch()
                          }}
                        >
                          Dismiss
                        </button>
                        <button
                          type="button"
                          className="btn-primary text-xs py-1.5"
                          onClick={async () => {
                            await removeReportedPost(r.id)
                            toast.success('Post removed')
                            reportsQuery.refetch()
                          }}
                        >
                          Remove post
                        </button>
                      </>
                    )}
                    {r.report_type === 'user' && (
                      <>
                        <button
                          type="button"
                          className="btn-secondary text-xs py-1.5"
                          onClick={async () => {
                            await dismissUserReport(r.id)
                            toast.success('Dismissed')
                            reportsQuery.refetch()
                          }}
                        >
                          Dismiss
                        </button>
                        <button
                          type="button"
                          className="btn-secondary text-xs py-1.5"
                          onClick={async () => {
                            await warnUserReport(r.id)
                            toast.success('Warned')
                            reportsQuery.refetch()
                          }}
                        >
                          Warn
                        </button>
                        <button
                          type="button"
                          className="btn-primary text-xs py-1.5"
                          onClick={async () => {
                            await suspendUserReport(r.id)
                            toast.success('Suspended')
                            reportsQuery.refetch()
                          }}
                        >
                          Suspend user
                        </button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {section === 'fraud' && (
          <div>
            <h1 className="text-xl font-bold mb-4">Fraud alerts</h1>
            <div className="space-y-2">
              {(fraudQuery.data?.alerts || []).map((u) => (
                <div key={u.user_id} className="glass p-4 flex justify-between items-center">
                  <div>
                    <p className="font-medium">{u.email}</p>
                    <p className="text-xs text-slate-400">
                      Risk {u.fraud_risk_score} ({u.risk_tier})
                    </p>
                  </div>
                  <button
                    type="button"
                    className="btn-primary text-xs py-1.5"
                    onClick={async () => {
                      try {
                        await confirmFraud(u.user_id)
                        toast.success('Fraud confirmed')
                        fraudQuery.refetch()
                      } catch (e) {
                        toast.error(e.response?.data?.detail || 'Failed')
                      }
                    }}
                  >
                    Confirm fraud
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {section === 'posts' && (
          <div>
            <h1 className="text-xl font-bold mb-4">Post moderation</h1>
            <div className="space-y-2">
              {(postsQuery.data?.posts || []).map((p) => (
                <div key={p.item_id} className="glass p-4 flex justify-between gap-3">
                  <div>
                    <p className="text-xs text-slate-400">{p.item_type} · {p.status}</p>
                    <p className="text-sm">{p.public_description}</p>
                    <p className="text-xs text-slate-500">
                      by {p.posted_by_name} · {p.pending_reports} report(s)
                    </p>
                  </div>
                  <button
                    type="button"
                    className="btn-primary text-xs py-1.5 shrink-0"
                    onClick={async () => {
                      try {
                        await forceClosePost(p.item_id, 'Admin force close')
                        toast.success('Force closed')
                        postsQuery.refetch()
                      } catch (e) {
                        toast.error(e.response?.data?.detail || 'Failed')
                      }
                    }}
                  >
                    Force close
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {section === 'logs' && isRoot && (
          <div>
            <h1 className="text-xl font-bold mb-4">Admin activity log</h1>
            <div className="space-y-2 text-sm">
              {(logsQuery.data?.logs || []).map((log) => (
                <div key={log.id} className="glass p-3">
                  <p className="text-slate-300">
                    <span className="text-brand-400">{log.action}</span>
                    {' · '}
                    {log.admin_email || 'system'}
                  </p>
                  <p className="text-xs text-slate-500">
                    {log.target_type} {log.target_id} · {new Date(log.created_at).toLocaleString()}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
