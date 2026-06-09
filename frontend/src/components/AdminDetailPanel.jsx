/**
 * Admin detail panel — renders full context for queue items.
 */
import { Link } from 'react-router-dom'

function Photos({ urls }) {
  if (!urls?.length) return <p className="text-xs text-slate-500">No photos</p>
  return (
    <div className="flex flex-wrap gap-2 mt-2">
      {urls.map((url) => (
        <a key={url} href={url} target="_blank" rel="noreferrer" className="block">
          <img
            src={url}
            alt=""
            className="w-24 h-24 object-cover rounded-lg border border-slate-700"
          />
        </a>
      ))}
    </div>
  )
}

function ItemBlock({ item, label }) {
  if (!item) return null
  return (
    <div className="glass p-3 mt-2">
      <p className="text-xs text-brand-400 uppercase">{label}</p>
      <p className="text-sm mt-1">{item.public_description}</p>
      <p className="text-xs text-slate-500 mt-1">
        {item.category} · {item.location_label} · {item.status}
      </p>
      <p className="text-xs text-slate-500">
        Posted {new Date(item.date_occurred).toLocaleDateString()}
      </p>
      {item.poster && (
        <p className="text-xs text-slate-400 mt-1">
          @{item.poster.username} · trust {item.poster.trust_score} ({item.poster.trust_tier})
          · fraud {item.poster.fraud_risk_score} ({item.poster.fraud_risk_tier})
        </p>
      )}
      <Photos urls={item.image_urls} />
    </div>
  )
}

function JsonBlock({ data, title }) {
  if (!data || (typeof data === 'object' && !Object.keys(data).length)) return null
  return (
    <div className="mt-3">
      <p className="text-xs text-slate-400 uppercase mb-1">{title}</p>
      <pre className="text-xs bg-slate-900/80 p-2 rounded-lg overflow-x-auto text-slate-300 max-h-48">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  )
}

function ItemList({ items, title, showPoster = false, limit = 10 }) {
  const list = (items || []).slice(0, limit)
  if (!list.length) {
    return (
      <div className="mt-3">
        <p className="text-xs text-slate-400 uppercase mb-1">{title}</p>
        <p className="text-xs text-slate-500">None</p>
      </div>
    )
  }
  return (
    <div className="mt-3">
      <p className="text-xs text-slate-400 uppercase mb-2">{title}</p>
      <div className="space-y-2 max-h-64 overflow-y-auto">
        {list.map((item) => (
          <div key={item.id} className="rounded-lg border border-slate-700/80 bg-slate-900/40 p-3">
            <div className="flex gap-3">
              {item.image_urls?.[0] ? (
                <img
                  src={item.image_urls[0]}
                  alt=""
                  className="w-14 h-14 object-cover rounded-md border border-slate-700 shrink-0"
                />
              ) : (
                <div className="w-14 h-14 rounded-md bg-slate-800 border border-slate-700 shrink-0 flex items-center justify-center text-[10px] text-slate-500">
                  No img
                </div>
              )}
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className={`text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded ${
                    item.item_type === 'lost'
                      ? 'bg-amber-500/20 text-amber-300'
                      : 'bg-emerald-500/20 text-emerald-300'
                  }`}>
                    {item.item_type}
                  </span>
                  <span className="text-[10px] text-slate-500 uppercase">{item.category}</span>
                  <span className="text-[10px] text-slate-500">· {item.status}</span>
                </div>
                <p className="text-sm text-slate-200 mt-1 line-clamp-2">{item.public_description}</p>
                <p className="text-xs text-slate-500 mt-0.5">
                  {item.location_label} · {new Date(item.date_occurred).toLocaleDateString()}
                </p>
                {showPoster && item.poster && (
                  <p className="text-xs text-slate-500 mt-0.5">@{item.poster.username}</p>
                )}
                <Link
                  to={`/items/${item.id}`}
                  className="text-[10px] text-brand-400 hover:underline mt-1 inline-block"
                >
                  View on site →
                </Link>
              </div>
            </div>
            {item.image_urls?.length > 1 && (
              <div className="flex gap-1.5 mt-2 pl-[3.75rem]">
                {item.image_urls.slice(1).map((url) => (
                  <a key={url} href={url} target="_blank" rel="noreferrer">
                    <img src={url} alt="" className="w-10 h-10 object-cover rounded border border-slate-700" />
                  </a>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function ReportList({ reports, title, showEscalated = false }) {
  const list = reports || []
  if (!list.length) {
    return (
      <div className="mt-3">
        <p className="text-xs text-slate-400 uppercase mb-1">{title}</p>
        <p className="text-xs text-slate-500">None</p>
      </div>
    )
  }
  return (
    <div className="mt-3">
      <p className="text-xs text-slate-400 uppercase mb-2">{title}</p>
      <div className="space-y-1.5 max-h-40 overflow-y-auto">
        {list.map((r) => (
          <div key={r.id} className="text-xs text-slate-400 border-l-2 border-slate-700 pl-2 py-0.5">
            <span className="text-slate-300">{r.reason}</span>
            {' · '}
            <span className="text-slate-500">{r.status}</span>
            {showEscalated && r.auto_escalated && (
              <span className="text-amber-400 ml-1">· escalated</span>
            )}
            {' · '}
            <span className="text-slate-600">{new Date(r.created_at).toLocaleString()}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function PostClaimsList({ claims }) {
  const list = claims || []
  if (!list.length) {
    return (
      <div className="mt-3">
        <p className="text-xs text-slate-400 uppercase mb-1">All claims</p>
        <p className="text-xs text-slate-500">None</p>
      </div>
    )
  }
  return (
    <div className="mt-3">
      <p className="text-xs text-slate-400 uppercase mb-2">All claims ({list.length})</p>
      <div className="space-y-2 max-h-64 overflow-y-auto">
        {list.map((c) => (
          <div
            key={c.match_id}
            className="rounded-lg border border-slate-700/80 bg-slate-900/40 p-3"
          >
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="text-brand-400 uppercase font-semibold">{c.path}</span>
              <span className={`px-1.5 py-0.5 rounded text-[10px] uppercase ${
                c.status === 'verified'
                  ? 'bg-emerald-500/20 text-emerald-300'
                  : c.status === 'pending_review'
                    ? 'bg-amber-500/20 text-amber-300'
                    : 'bg-slate-700 text-slate-400'
              }`}>
                {c.status?.replace(/_/g, ' ')}
              </span>
              <span className="text-slate-400">score {c.match_score}</span>
            </div>
            {c.claimant ? (
              <>
                <p className="text-sm text-slate-200 mt-1.5">
                  {c.claimant.full_name}
                  <span className="text-slate-500"> @{c.claimant.username}</span>
                </p>
                <p className="text-xs text-slate-500 mt-0.5">
                  Trust {c.claimant.trust_score} ({c.claimant.trust_tier})
                  {' · '}
                  Fraud {c.claimant.fraud_risk_score} ({c.claimant.fraud_risk_tier})
                </p>
              </>
            ) : (
              <p className="text-xs text-slate-500 mt-1.5">Claimant unknown</p>
            )}
            <p className="text-[10px] text-slate-600 mt-1">
              {new Date(c.created_at).toLocaleString()}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}

function StatusHistoryList({ history }) {
  const list = history || []
  if (!list.length) {
    return (
      <div className="mt-3">
        <p className="text-xs text-slate-400 uppercase mb-1">Status history</p>
        <p className="text-xs text-slate-500">No recorded changes</p>
      </div>
    )
  }
  return (
    <div className="mt-3">
      <p className="text-xs text-slate-400 uppercase mb-2">Status history</p>
      <div className="space-y-2 max-h-48 overflow-y-auto">
        {list.map((entry, idx) => (
          <div
            key={`${entry.at}-${entry.event}-${idx}`}
            className="flex gap-3 text-xs border-l-2 border-slate-700 pl-3 py-0.5"
          >
            <div className="min-w-0 flex-1">
              <p className="text-slate-300 capitalize">{entry.event?.replace(/_/g, ' ')}</p>
              {entry.detail?.status && (
                <p className="text-slate-500 mt-0.5">Status: {entry.detail.status}</p>
              )}
              {entry.detail?.status_before && entry.detail?.status_after && (
                <p className="text-slate-500 mt-0.5">
                  {entry.detail.status_before} → {entry.detail.status_after}
                </p>
              )}
              {entry.detail?.action && !entry.detail?.status_before && (
                <p className="text-slate-600 mt-0.5">{entry.detail.action}</p>
              )}
            </div>
            <p className="text-slate-600 shrink-0 text-[10px]">
              {new Date(entry.at).toLocaleString()}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}

function ClaimsSummary({ claims }) {
  if (!claims) return null
  const pathA = claims.path_a_attempts || []
  const pathB = claims.path_b || []
  const pathC = claims.path_c || []
  const total = pathA.length + pathB.length + pathC.length
  if (!total) {
    return (
      <div className="mt-3">
        <p className="text-xs text-slate-400 uppercase mb-1">Claims made</p>
        <p className="text-xs text-slate-500">None</p>
      </div>
    )
  }
  return (
    <div className="mt-3">
      <p className="text-xs text-slate-400 uppercase mb-2">Claims made ({total})</p>
      <div className="space-y-1 max-h-32 overflow-y-auto text-xs text-slate-400">
        {pathA.map((c) => (
          <p key={c.id}>Path A · {c.result} · score {c.ownership_score}</p>
        ))}
        {pathB.map((c) => (
          <p key={c.id}>Path B · {c.result} · score {c.ownership_score}</p>
        ))}
        {pathC.map((c) => (
          <p key={c.id}>Path C · {c.result} · score {c.ownership_score}</p>
        ))}
      </div>
    </div>
  )
}

export function ClaimDetail({ detail, actions }) {
  if (!detail) return null
  return (
    <div>
      <p className="text-xs text-brand-400 uppercase">{detail.path}</p>
      <p className="text-sm text-slate-400 mt-1">{detail.scoring_formula}</p>
      <p className="text-sm mt-2">Score: {detail.match_score}</p>
      {detail.claimant && (
        <p className="text-xs text-slate-500">
          Claimant: {detail.claimant.full_name} (@{detail.claimant.username})
        </p>
      )}
      <ItemBlock item={detail.lost_item} label="Lost item" />
      <ItemBlock item={detail.found_item} label="Found item" />
      <JsonBlock data={detail.evidence} title="Evidence & scores" />
      {actions}
    </div>
  )
}

function ClaimantsList({ claimants }) {
  if (!claimants?.length) return null
  return (
    <div className="mt-3">
      <p className="text-xs text-slate-400 uppercase mb-2">Claimants in dispute</p>
      <div className="space-y-2">
        {claimants.map((c) => (
          <div key={c.match_id} className="rounded-lg border border-slate-700/80 bg-slate-900/40 p-3 text-xs">
            <p className="text-slate-200 font-medium">
              {c.claimant?.full_name || 'Unknown'} (@{c.claimant?.username || '?'})
            </p>
            <p className="text-slate-500 mt-0.5">
              {c.path} · score {c.match_score} · status {c.status}
            </p>
            <p className="text-slate-600 mt-0.5">
              Trust {c.claimant?.trust_score} · Fraud {c.claimant?.fraud_risk_score}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}

function VerificationHistory({ rows }) {
  if (!rows?.length) return null
  return (
    <div className="mt-3 max-h-48 overflow-y-auto">
      <p className="text-xs text-slate-400 uppercase mb-2">Verification history</p>
      <div className="space-y-1.5">
        {rows.map((v) => (
          <div key={v.id} className="text-xs text-slate-400 border-l-2 border-slate-700 pl-2">
            <span className="text-slate-300">{v.path}</span>
            {' · '}
            {v.result} · score {v.ownership_score}
            {' · '}
            <span className="text-slate-600">{new Date(v.created_at).toLocaleString()}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function ReturnStateBlock({ state }) {
  if (!state) return null
  return (
    <div className="mt-3 text-xs text-slate-400 space-y-1">
      <p className="text-slate-400 uppercase">Return state</p>
      <p>Returned: {state.returned_at ? new Date(state.returned_at).toLocaleString() : '—'}</p>
      <p>Finder handed over: {state.finder_handed_over_at ? new Date(state.finder_handed_over_at).toLocaleString() : '—'}</p>
      <p>Owner received: {state.owner_received_at ? new Date(state.owner_received_at).toLocaleString() : '—'}</p>
      <p>Method: {state.method || '—'} · Tip frozen: {state.tip_frozen ? 'yes' : 'no'}</p>
    </div>
  )
}

export function DisputeDetail({ detail, actions }) {
  if (!detail) return null
  return (
    <div>
      <p className="text-xs text-brand-400 uppercase">{detail.dispute_type} dispute</p>
      <p className="text-sm mt-2">{detail.dispute_reason}</p>
      <ItemBlock item={detail.lost_item} label="Lost item" />
      <ItemBlock item={detail.found_item} label="Found item" />
      <ReturnStateBlock state={detail.return_state} />
      {detail.qr_logs && <JsonBlock data={detail.qr_logs} title="QR logs" />}
      <ClaimantsList claimants={detail.claimants} />
      {detail.chat_history?.length > 0 && (
        <div className="mt-3 max-h-40 overflow-y-auto space-y-1">
          <p className="text-xs text-slate-400 uppercase">Chat history</p>
          {detail.chat_history.map((m) => (
            <p key={m.id} className="text-xs text-slate-400">
              <span className="text-slate-300">{m.sender_name}:</span> {m.body}
            </p>
          ))}
        </div>
      )}
      <VerificationHistory rows={detail.verification_history} />
      {actions}
    </div>
  )
}

export function ReportDetail({ detail, actions }) {
  if (!detail) return null
  const r = detail.report
  return (
    <div>
      <p className="text-xs text-brand-400 uppercase">{detail.report_type} report</p>
      <p className="text-sm mt-1">{r.reason} — {r.detail_text || 'No details'}</p>
      {r.auto_escalated && (
        <span className="text-xs text-amber-400">Priority — auto-escalated</span>
      )}
      {detail.target_item && <ItemBlock item={detail.target_item} label="Reported post" />}
      {detail.target_user && (
        <p className="text-sm mt-2">
          Reported user: {detail.target_user.full_name} (@{detail.target_user.username})
        </p>
      )}
      <JsonBlock data={detail.report_history_on_target} title="All reports on target" />
      {actions}
    </div>
  )
}

export function FraudDetail({ detail, actions }) {
  if (!detail) return null
  return (
    <div>
      <p className="text-sm font-medium">{detail.user?.email}</p>
      <p className="text-xs text-slate-400">
        Risk {detail.fraud_risk_score} ({detail.fraud_risk_tier}) · Trust {detail.trust_score}
      </p>
      <div className="mt-3 max-h-64 overflow-y-auto space-y-1">
        <p className="text-xs text-slate-400 uppercase">Fraud event history</p>
        {(detail.fraud_events || []).map((e) => (
          <p key={e.id} className="text-xs text-slate-500">
            {new Date(e.created_at).toLocaleString()} — {e.signal_type} ({e.delta >= 0 ? '+' : ''}{e.delta}) → {e.score_after}
          </p>
        ))}
      </div>
      {actions}
    </div>
  )
}

export function PostDetail({ detail, actions }) {
  if (!detail) return null
  const item = detail.item
  return (
    <div>
      <ItemBlock item={item} label="Post" />
      {detail.pending_reports > 0 && (
        <p className="text-xs text-amber-400 mt-2">
          {detail.pending_reports} pending report{detail.pending_reports !== 1 ? 's' : ''}
        </p>
      )}
      <PostClaimsList claims={detail.claims} />
      <ReportList reports={detail.reports} title="All reports" showEscalated />
      <StatusHistoryList history={detail.status_history} />
      <Link
        to={`/items/${item?.id}`}
        className="text-xs text-brand-400 hover:underline mt-3 inline-block"
      >
        View on main site →
      </Link>
      {actions}
    </div>
  )
}

export function UserDetailPanel({ detail, actions }) {
  if (!detail) return null
  const p = detail.profile
  return (
    <div>
      <p className="font-medium">{p.full_name}</p>
      <p className="text-xs text-slate-400">{p.email} · @{p.username}</p>
      <p className="text-xs text-slate-500 mt-1">
        Trust {detail.trust_score} ({detail.trust_tier}) · Fraud {detail.fraud_risk_score} ({detail.fraud_risk_tier})
      </p>
      <div className="mt-3 max-h-32 overflow-y-auto">
        <p className="text-xs text-slate-400 uppercase">Trust history</p>
        {(detail.trust_events || []).slice(0, 10).map((e) => (
          <p key={e.id} className="text-xs text-slate-500">
            {new Date(e.created_at).toLocaleString()} — {e.reason}{' '}
            ({e.delta >= 0 ? '+' : ''}{e.delta})
          </p>
        ))}
      </div>
      <div className="mt-3 max-h-32 overflow-y-auto">
        <p className="text-xs text-slate-400 uppercase">Fraud history</p>
        {(detail.fraud_events || []).slice(0, 10).map((e) => (
          <p key={e.id} className="text-xs text-slate-500">
            {e.signal_type} ({e.delta >= 0 ? '+' : ''}{e.delta})
          </p>
        ))}
      </div>
      <ItemList items={detail.items_posted} title="Recent posts" limit={10} />
      <ClaimsSummary claims={detail.claims} />
      <ReportList reports={detail.reports_received} title="Reports received" />
      {(detail.reports_made?.post?.length > 0 || detail.reports_made?.user?.length > 0) && (
        <div className="mt-3">
          <p className="text-xs text-slate-400 uppercase mb-1">Reports made</p>
          <p className="text-xs text-slate-500">
            {detail.reports_made.post?.length || 0} post · {detail.reports_made.user?.length || 0} user
          </p>
        </div>
      )}
      {actions}
    </div>
  )
}

export default function AdminDetailPanel({ section, detail, loading, children }) {
  if (!detail && !loading) {
    return (
      <div className="glass p-6 text-sm text-slate-500 h-full flex items-center justify-center">
        Select an item to view full details
      </div>
    )
  }
  return (
    <div className="glass p-4 overflow-y-auto max-h-[calc(100vh-8rem)]">
      <h2 className="text-sm font-semibold text-slate-300 mb-3 capitalize">{section} detail</h2>
      {loading && !detail ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : (
        children
      )}
    </div>
  )
}
