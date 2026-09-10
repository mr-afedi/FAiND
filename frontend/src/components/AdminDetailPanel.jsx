/**
 * Admin detail panel — renders full context for queue items.
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import ImageLightbox, { LightboxImage } from './ImageLightbox'
import {
  formatScorePct,
  statusColor,
} from '../utils/adminFormat'

function RecentActions({ actions }) {
  if (!actions?.length) return null
  return (
    <div className="mt-3 border-t border-slate-800 pt-3">
      <p className="text-xs text-slate-400 uppercase mb-2">Recent admin actions</p>
      <div className="space-y-1.5">
        {actions.map((a, i) => (
          <p key={`${a.action}-${i}`} className="text-xs text-slate-500">
            <span className="text-slate-700 dark:text-slate-300 capitalize">{a.action.replace(/_/g, ' ')}</span>
            {' by '}
            <span className="text-brand-400">{a.admin_email}</span>
            {' · '}
            {new Date(a.created_at).toLocaleString()}
          </p>
        ))}
      </div>
    </div>
  )
}

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
    <div className="admin-detail-block">
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
          @{item.poster.username}
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
      <pre className="text-xs bg-slate-900/80 p-2 rounded-lg overflow-x-auto text-slate-700 dark:text-slate-300 max-h-48">
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
                <p className="text-sm text-slate-800 dark:text-slate-200 mt-1 line-clamp-2">{item.public_description}</p>
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
            <span className="text-slate-700 dark:text-slate-300">{r.reason}</span>
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

function PostMatchesList({ matches }) {
  const list = matches || []
  if (!list.length) {
    return (
      <div className="mt-3">
        <p className="text-xs text-slate-400 uppercase mb-1">AI matches</p>
        <p className="text-xs text-slate-500">None</p>
      </div>
    )
  }
  return (
    <div className="mt-3">
      <p className="text-xs text-slate-400 uppercase mb-2">AI matches ({list.length})</p>
      <div className="space-y-2 max-h-64 overflow-y-auto">
        {list.map((m) => (
          <div
            key={m.match_id}
            className="rounded-lg border border-slate-700/80 bg-slate-900/40 p-3"
          >
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className={`px-1.5 py-0.5 rounded text-[10px] uppercase ${
                m.status === 'verified'
                  ? 'bg-emerald-500/20 text-emerald-300'
                  : m.status === 'pending_review'
                    ? 'bg-amber-500/20 text-amber-300'
                    : 'bg-slate-700 text-slate-400'
              }`}>
                {m.status?.replace(/_/g, ' ')}
              </span>
              <span className="text-slate-400">score {formatScorePct(m.match_score)}</span>
            </div>
            <p className="text-[10px] text-slate-600 mt-1">
              {new Date(m.created_at).toLocaleString()}
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
              <p className="text-slate-700 dark:text-slate-300 capitalize">{entry.event?.replace(/_/g, ' ')}</p>
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

function ReturnStateBlock({ state }) {
  if (!state) return null
  return (
    <div className="mt-3 text-xs text-slate-400 space-y-1">
      <p className="text-slate-400 uppercase">Return state</p>
      <p>Returned: {state.returned_at ? new Date(state.returned_at).toLocaleString() : '—'}</p>
      <p>Finder handed over: {state.finder_handed_over_at ? new Date(state.finder_handed_over_at).toLocaleString() : '—'}</p>
      <p>Owner received: {state.owner_received_at ? new Date(state.owner_received_at).toLocaleString() : '—'}</p>
      <p>Method: {state.method || '—'}</p>
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
      {detail.reports_on_parties && (
        <JsonBlock data={detail.reports_on_parties} title="Reports involving parties" />
      )}
      <RecentActions actions={detail.recent_actions} />
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
      {r.reporter && (
        <p className="text-xs text-slate-500 mt-1">
          Reporter: @{r.reporter.username}
        </p>
      )}
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
      <RecentActions actions={detail.recent_actions} />
      {actions}
    </div>
  )
}

export function ReturnedDetail({ detail, actions, onGoToDispute }) {
  if (!detail) return null
  const lost = detail.lost_item
  const found = detail.found_item
  const d = detail.dispute || {}
  const handover = detail.handover
  const claim = detail.claim
  return (
    <div>
      {lost ? (
        <ItemBlock item={lost} label="Lost item (returned)" />
      ) : (
        <ItemBlock item={found} label="Returned item" />
      )}
      {found && lost && (
        <ItemBlock item={found} label="Found item" />
      )}
      <div className="admin-detail-block mt-2 text-xs space-y-1">
        <p>
          <span className="text-slate-500">Owner</span>{' '}
          @{detail.owner?.username}
          {detail.owner?.full_name ? ` (${detail.owner.full_name})` : ''}
        </p>
        <p>
          <span className="text-slate-500">Finder</span>{' '}
          {detail.finder?.username ? `@${detail.finder.username}` : (detail.finder?.full_name || 'Anonymous finder')}
        </p>
        {detail.drop_point_name && (
          <p><span className="text-slate-500">Drop point</span> {detail.drop_point_name}</p>
        )}
        <p><span className="text-slate-500">Location lost</span> {detail.location_lost || '—'}</p>
        <p><span className="text-slate-500">Location found</span> {detail.location_found || '—'}</p>
        <p>
          <span className="text-slate-500">Dates</span>{' '}
          {detail.date_posted && (
            <>posted {new Date(detail.date_posted).toLocaleDateString()} · </>
          )}
          {detail.date_dropped_off && (
            <>dropped off {new Date(detail.date_dropped_off).toLocaleString()} · </>
          )}
          lost {detail.date_lost ? new Date(detail.date_lost).toLocaleDateString() : '—'}
          {' · '}
          found {detail.date_found ? new Date(detail.date_found).toLocaleDateString() : '—'}
          {' · '}
          returned {detail.date_returned ? new Date(detail.date_returned).toLocaleString() : '—'}
        </p>
        <p><span className="text-slate-500">Confirmed via</span> {detail.return_method || '—'}</p>
        {claim && (
          <p>
            <span className="text-slate-500">Claim path</span> {claim.claim_path}
            {claim.claim_path === 'A' && claim.ai_confidence_score != null && (
              <> · AI score {(claim.ai_confidence_score * 100).toFixed(0)}%</>
            )}
          </p>
        )}
      </div>
      {handover && (
        <div className="admin-detail-block mt-3 text-xs space-y-2">
          <p className="text-slate-400 uppercase text-[10px] tracking-wide">Handover capture</p>
          <p><span className="text-slate-500">Claimant</span> {handover.claimant_name}</p>
          <p><span className="text-slate-500">Phone</span> {handover.claimant_phone}</p>
          {handover.claimant_student_id && (
            <p><span className="text-slate-500">Student ID</span> {handover.claimant_student_id}</p>
          )}
          {handover.completed_at && (
            <p><span className="text-slate-500">Handover at</span> {new Date(handover.completed_at).toLocaleString()}</p>
          )}
          {handover.authority_override && (
            <p className="text-amber-400">Authority override — owner did not sign digitally</p>
          )}
          <div className="flex flex-wrap gap-2 mt-2">
            {handover.condition_photo_url && (
              <img src={handover.condition_photo_url} alt="Condition at handover" className="w-24 h-24 object-cover rounded-lg border border-slate-700" />
            )}
            {handover.claimant_photo_url && (
              <img src={handover.claimant_photo_url} alt="Claimant at handover" className="w-24 h-24 object-cover rounded-lg border border-slate-700" />
            )}
          </div>
        </div>
      )}
      {d.had_dispute && (
        <div className="mt-3 text-xs">
          <p className="text-slate-400 uppercase mb-1">Dispute history</p>
          {d.filed_at && (
            <p className="text-slate-500">
              Filed {new Date(d.filed_at).toLocaleString()}
              {d.reason ? ` — ${d.reason}` : ''}
            </p>
          )}
          {d.resolved_at && (
            <p className="text-slate-500">
              Resolved {new Date(d.resolved_at).toLocaleString()}
              {d.resolution_note ? ` — ${d.resolution_note}` : ''}
            </p>
          )}
          {d.open && d.dispute_type && onGoToDispute && (
            <button
              type="button"
              className="text-brand-400 hover:underline mt-1"
              onClick={() => onGoToDispute(d.return_id, d.dispute_type)}
            >
              Open in Disputes tab →
            </button>
          )}
        </div>
      )}
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
      <PostMatchesList matches={detail.matches} />
      <ReportList reports={detail.reports} title="All reports" showEscalated />
      <StatusHistoryList history={detail.status_history} />
      <Link
        to={`/items/${item?.id}`}
        className="text-xs text-brand-400 hover:underline mt-3 inline-block"
      >
        View on main site →
      </Link>
      <RecentActions actions={detail.recent_actions} />
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
      <ItemList items={detail.items_posted} title="Recent posts" limit={10} />
      <ReportList reports={detail.reports_received} title="Reports received" />
      {(detail.reports_made?.post?.length > 0 || detail.reports_made?.user?.length > 0) && (
        <div className="mt-3">
          <p className="text-xs text-slate-400 uppercase mb-1">Reports made</p>
          <p className="text-xs text-slate-500">
            {detail.reports_made.post?.length || 0} post · {detail.reports_made.user?.length || 0} user
          </p>
        </div>
      )}
      <RecentActions actions={detail.recent_actions} />
      {actions}
    </div>
  )
}

function ClaimStatusBadge({ status }) {
  const labels = {
    pending: 'Pending review',
    called_to_collect: 'Called to collect',
    verified: 'Verified',
    rejected: 'Rejected',
  }
  return (
    <span className={`text-[10px] font-semibold uppercase ${statusColor(status)}`}>
      {labels[status] || status?.replace(/_/g, ' ')}
    </span>
  )
}

function AdminPhotoGrid({ urls, onOpen, className = '' }) {
  if (!urls?.length) return <p className="text-xs text-slate-500">No photos</p>
  return (
    <div className={`flex flex-wrap gap-2 ${className}`}>
      {urls.map((url, i) => (
        <LightboxImage
          key={url}
          src={url}
          images={urls}
          index={i}
          onOpen={onOpen}
          className="w-24 h-24 rounded-lg overflow-hidden border border-slate-700"
        />
      ))}
    </div>
  )
}

function ClaimantEvidenceCard({ claimant, onOpen }) {
  return (
    <article className="rounded-lg border border-slate-700/80 bg-slate-900/40 p-3 flex flex-col gap-2 min-w-[240px] flex-1">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">@{claimant.username}</p>
          {claimant.full_name && (
            <p className="text-xs text-slate-500">{claimant.full_name}</p>
          )}
        </div>
        <ClaimStatusBadge status={claimant.display_status} />
      </div>
      <p className="text-xs text-slate-400">
        Path {claimant.claim_path}
        {claimant.trust_tier ? ` · Trust: ${claimant.trust_tier}` : ''}
      </p>
      <p className="text-sm text-slate-700 dark:text-slate-300 leading-snug">{claimant.description}</p>
      {claimant.photo_url && (
        <LightboxImage
          src={claimant.photo_url}
          images={[claimant.photo_url]}
          onOpen={onOpen}
          className="w-full max-w-[160px] aspect-square rounded-lg overflow-hidden border border-slate-700"
        />
      )}
      <div className="text-xs text-slate-500 space-y-0.5 mt-auto">
        <p>
          Lost {claimant.date_lost ? new Date(claimant.date_lost).toLocaleDateString() : '—'}
          {claimant.time_lost ? ` at ${claimant.time_lost}` : ''}
        </p>
        {claimant.claim_path === 'C' && claimant.lost_location && (
          <p>Location lost: {claimant.lost_location}</p>
        )}
        {claimant.claim_path === 'A' && claimant.ai_confidence_score != null && (
          <p>AI confidence: {formatScorePct(claimant.ai_confidence_score)}</p>
        )}
        <p>Submitted {new Date(claimant.created_at).toLocaleString()}</p>
      </div>
    </article>
  )
}

export function ClaimDetail({ detail }) {
  const [lightbox, setLightbox] = useState(null)
  if (!detail) return null

  const item = detail.found_item
  const finder = detail.finder
  const openLightbox = (images, index = 0) => setLightbox({ images, index })

  return (
    <div className="space-y-4">
      {lightbox && (
        <ImageLightbox
          images={lightbox.images}
          startIdx={lightbox.index}
          onClose={() => setLightbox(null)}
        />
      )}

      <div>
        <p className="text-xs text-brand-400 uppercase mb-2">Found item</p>
        <p className="text-sm text-slate-800 dark:text-slate-200 leading-snug">{item?.public_description}</p>
        <div className="text-xs text-slate-500 mt-2 space-y-0.5">
          <p>
            {item?.category?.replace(/_/g, ' ')} · {item?.status?.replace(/_/g, ' ')}
          </p>
          <p>Location found: {item?.location_label || '—'}</p>
          <p>
            Date found:{' '}
            {item?.date_found
              ? new Date(item.date_found).toLocaleDateString()
              : '—'}
          </p>
          <p>Drop point: {item?.drop_point_name || '—'}</p>
          {item?.authority_received_at && (
            <p>Received at drop point: {new Date(item.authority_received_at).toLocaleString()}</p>
          )}
          <p>
            Finder:{' '}
            {finder?.username
              ? `@${finder.username}${finder.full_name ? ` (${finder.full_name})` : ''}`
              : (finder?.full_name || 'Anonymous Finder')}
          </p>
        </div>
        <AdminPhotoGrid urls={item?.image_urls} onOpen={openLightbox} className="mt-2" />
      </div>

      <div>
        <p className="text-xs text-brand-400 uppercase mb-2">
          Claimants ({detail.claimants?.length || 0})
        </p>
        <div className="flex gap-3 overflow-x-auto pb-1">
          {(detail.claimants || []).map((c) => (
            <ClaimantEvidenceCard key={c.claim_id} claimant={c} onOpen={openLightbox} />
          ))}
        </div>
      </div>

      {detail.authorities?.length > 0 && (
        <div className="text-xs space-y-1">
          <p className="text-slate-400 uppercase text-[10px] tracking-wide">Authority</p>
          {detail.authorities.map((a) => (
            <p key={a.authority_id} className="text-slate-400">
              {a.email}
              {a.drop_point_name ? ` · ${a.drop_point_name}` : ''}
            </p>
          ))}
        </div>
      )}

      {detail.timeline?.length > 0 && (
        <div>
          <p className="text-xs text-slate-400 uppercase mb-2">Authority timeline</p>
          <div className="space-y-2">
            {detail.timeline.map((entry, i) => (
              <div key={`${entry.event}-${entry.at}-${i}`} className="text-xs border-l-2 border-slate-700 pl-3">
                <p className="text-slate-700 dark:text-slate-300">{entry.label}</p>
                <p className="text-slate-500 mt-0.5">
                  {entry.at ? new Date(entry.at).toLocaleString() : '—'}
                  {entry.actor ? ` · ${entry.actor}` : ''}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {detail.is_returned && detail.handover && (
        <div className="admin-detail-block text-xs space-y-2">
          <p className="text-slate-400 uppercase text-[10px] tracking-wide">Handover</p>
          <p><span className="text-slate-500">Claimant</span> {detail.handover.claimant_name}</p>
          <p><span className="text-slate-500">Phone</span> {detail.handover.claimant_phone}</p>
          {detail.handover.claimant_student_id && (
            <p><span className="text-slate-500">Student ID</span> {detail.handover.claimant_student_id}</p>
          )}
          {detail.handover.completed_at && (
            <p>
              <span className="text-slate-500">Completed</span>{' '}
              {new Date(detail.handover.completed_at).toLocaleString()}
            </p>
          )}
          {detail.handover.authority_override && (
            <p className="text-amber-400">
              Authority override — owner did not sign digitally
              {detail.handover.authority_override_note
                ? `: ${detail.handover.authority_override_note}`
                : ''}
            </p>
          )}
          <div className="flex flex-wrap gap-2 mt-2">
            {detail.handover.condition_photo_url && (
              <LightboxImage
                src={detail.handover.condition_photo_url}
                images={[detail.handover.condition_photo_url]}
                onOpen={openLightbox}
                className="w-24 h-24 rounded-lg overflow-hidden border border-slate-700"
              />
            )}
            {detail.handover.claimant_photo_url && (
              <LightboxImage
                src={detail.handover.claimant_photo_url}
                images={[detail.handover.claimant_photo_url]}
                onOpen={openLightbox}
                className="w-24 h-24 rounded-lg overflow-hidden border border-slate-700"
              />
            )}
          </div>
        </div>
      )}

      {item?.id && (
        <Link to={`/items/${item.id}`} className="text-xs text-brand-400 hover:underline inline-block">
          View on main site →
        </Link>
      )}
    </div>
  )
}

export default function AdminDetailPanel({ section, detail, loading, children }) {
  if (!detail && !loading) {
    return (
      <div className="admin-detail-panel min-h-[12rem] text-sm text-slate-500 flex items-center justify-center">
        Select an item to view full details
      </div>
    )
  }
  return (
    <div className="admin-detail-panel max-h-[calc(100vh-11rem)] min-w-0">
      <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">{section} detail</h2>
      {loading && !detail ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : (
        children
      )}
    </div>
  )
}
