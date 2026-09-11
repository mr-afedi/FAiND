/**
 * Authority Dashboard — Section 17.1 (W7).
 */
import { useState, useCallback, useEffect, useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useAuthorityAuth } from '../context/AuthorityAuthContext'
import AuthorityQrScanner from '../components/AuthorityQrScanner'
import AuthorityHandoverTab from '../components/AuthorityHandoverTab'
import ThemeToggleButton from '../components/ThemeToggleButton'
import StaffPushSettingsToggle from '../components/StaffPushSettingsToggle'
import StaffPushPromptBanner from '../components/StaffPushPromptBanner'
import AuthorityPushPromptTrigger from '../components/AuthorityPushPromptTrigger'
import AuthorityClaimsTab from '../components/AuthorityClaimsTab'
import AuthorityAlertsBell from '../components/AuthorityAlertsBell'
import SubmitButton from '../components/SubmitButton'
import { useSubmitLock } from '../hooks/useSubmitLock'
import { getCategoryLabel, CategoryIcon } from '../components/icons'
import { MapPin, Clock, QrCode } from 'lucide-react'
import {
  getAuthorityIncoming,
  getAuthorityAtDroppoint,
  getAuthorityClaimsList,
  getAuthorityHandoverQueue,
  confirmAuthorityDropoff,
  scanAuthorityQr,
  getAuthorityDropPointSettings,
  updateAuthorityDropPointSettings,
  getAuthorityAlerts,
} from '../services/authorityService'
import { AuthorityLightboxProvider, useAuthorityLightbox } from '../context/AuthorityLightboxContext'
import { LightboxImage } from '../components/ImageLightbox'
import { invalidateAfterDropOff } from '../utils/queryCache'
import StaffBottomNav, { AUTHORITY_NAV } from '../components/staff-mobile/StaffBottomNav'
import StaffMobileBottomSheet from '../components/staff-mobile/StaffMobileBottomSheet'
import StaffDesktopDetailModal from '../components/staff-mobile/StaffDesktopDetailModal'
import {
  StaffIncomingMobileCard,
  StaffAtDroppointMobileCard,
} from '../components/staff-mobile/StaffMobileItemCard'
import StaffAlertsPanel from '../components/staff-mobile/StaffAlertsPanel'
import { timeSincePosted } from '../components/staff-mobile/staffUtils'

const TABS = [
  { id: 'incoming', label: 'Incoming' },
  { id: 'at-droppoint', label: 'At Drop Point' },
  { id: 'claims', label: 'Claims' },
  { id: 'handover', label: 'Handover' },
  { id: 'settings', label: 'Settings' },
]

function formatWhen(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString()
}

function DropoffCountdown({ item }) {
  if (item.dropoff_phase === 'finder_confirmed') {
    return (
      <p className="text-xs text-sky-800 bg-sky-50 border border-sky-200 dark:text-sky-300 dark:bg-sky-900/30 dark:border-sky-800 rounded-lg px-3 py-2">
        Finder marked drop-off — awaiting your receipt confirmation.
      </p>
    )
  }

  if (item.dropoff_hours_remaining > 0) {
    return (
      <p className="text-sm text-slate-700 dark:text-slate-300">
        <strong className="text-slate-900 dark:text-slate-100">{item.dropoff_hours_remaining}</strong>
        {' '}hour{item.dropoff_hours_remaining !== 1 ? 's' : ''} left in the finder&apos;s 48h window.
      </p>
    )
  }

  if (item.dropoff_hours_until_unconfirmed > 0) {
    return (
      <p className="text-sm text-amber-700 dark:text-amber-300">
        Past 48h — finder can still drop off for{' '}
        <strong>{item.dropoff_hours_until_unconfirmed}</strong> more hour
        {item.dropoff_hours_until_unconfirmed !== 1 ? 's' : ''}.
      </p>
    )
  }

  return null
}

function IncomingItemCard({ item, onConfirm, confirmingId, onImageOpen, onOpenDetail }) {
  return (
    <article className="hidden md:block glass p-5 space-y-3 border border-slate-800/80">
      <button
        type="button"
        className="w-full text-left space-y-3"
        onClick={() => onOpenDetail?.(item)}
      >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-xs text-slate-500 uppercase tracking-wide">
            {getCategoryLabel(item.category)}
            {item.tracking_reference && (
              <span className="ml-2 font-mono text-slate-400">{item.tracking_reference}</span>
            )}
          </p>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100 mt-1">{item.public_description}</h3>
        </div>
        <span className={`text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full
          ${item.status === 'overdue'
            ? 'bg-amber-900/40 text-amber-200'
            : 'bg-slate-800 text-slate-700 dark:text-slate-300'}`}>
          {item.status}
        </span>
      </div>

      <p className="text-xs text-slate-400">
        Location: <span className="text-slate-700 dark:text-slate-300">{item.location_label}</span>
        {' · '}Reported {formatWhen(item.created_at)}
      </p>

      {item.image_urls?.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {item.image_urls.map((url, i) => (
            <LightboxImage
              key={url}
              src={url}
              images={item.image_urls}
              index={i}
              onOpen={onImageOpen}
              className="w-16 h-16 rounded-lg overflow-hidden border border-slate-700"
            />
          ))}
        </div>
      )}

      <DropoffCountdown item={item} />
      <p className="text-xs text-brand-400">Tap for full details</p>
      </button>

      {item.can_authority_confirm && (
        <button
          type="button"
          onClick={() => onConfirm(item.id)}
          disabled={confirmingId === item.id}
          className="btn-primary text-sm w-full sm:w-auto"
        >
          {confirmingId === item.id ? 'Confirming…' : 'Confirm received'}
        </button>
      )}

      {item.authority_received_at && !item.dropoff_confirmed_at && (
        <p className="text-xs text-slate-500">
          You confirmed receipt — waiting for finder drop-off confirmation.
        </p>
      )}
    </article>
  )
}

function AtDroppointItemCard({ item, onImageOpen, onOpenDetail }) {
  return (
    <article className="hidden md:block glass p-5 space-y-2 border border-emerald-900/40">
      <button
        type="button"
        className="w-full text-left space-y-2"
        onClick={() => onOpenDetail?.(item)}
      >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-xs text-slate-500 uppercase tracking-wide">
            {getCategoryLabel(item.category)}
          </p>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100 mt-1">{item.public_description}</h3>
        </div>
        <span className="text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full
                         bg-emerald-900/40 text-emerald-200">
          Awaiting claim
        </span>
      </div>
      <p className="text-xs text-slate-400">
        Received {formatWhen(item.dropoff_confirmed_at || item.authority_received_at)}
        {item.dropoff_late && (
          <span className="text-amber-400 ml-2">(late drop-off)</span>
        )}
      </p>
      {item.image_urls?.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {item.image_urls.map((url, i) => (
            <LightboxImage
              key={url}
              src={url}
              images={item.image_urls}
              index={i}
              onOpen={onImageOpen}
              className="w-16 h-16 rounded-lg overflow-hidden border border-slate-700"
            />
          ))}
        </div>
      )}
      {item.tracking_reference && (
        <p className="text-xs font-mono text-slate-500">{item.tracking_reference}</p>
      )}
      <p className="text-xs text-brand-400">Tap for full details</p>
      </button>
    </article>
  )
}

function PlaceholderTab({ title, note }) {
  return (
    <div className="glass p-8 text-center">
      <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">{title}</p>
      <p className="text-sm text-slate-500 mt-2">{note}</p>
    </div>
  )
}

function SettingsTab({ onAlertNavigate }) {
  const queryClient = useQueryClient()
  const { isSubmitting, tryAcquire, release } = useSubmitLock()

  const { data, isLoading } = useQuery({
    queryKey: ['authority-drop-point-settings'],
    queryFn: getAuthorityDropPointSettings,
  })

  const [hours, setHours] = useState('')
  const [closed, setClosed] = useState(false)
  const [reason, setReason] = useState('')

  useEffect(() => {
    if (!data) return
    setHours(data.operating_hours || '')
    setClosed(Boolean(data.is_temporarily_closed))
    setReason(data.closed_reason || '')
  }, [data])

  const { mutate: saveSettings } = useMutation({
    mutationFn: updateAuthorityDropPointSettings,
    onSuccess: (updated) => {
      queryClient.setQueryData(['authority-drop-point-settings'], updated)
      toast.success('Drop point settings saved')
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Could not save settings'),
    onSettled: () => release(),
  })

  function handleSubmit(e) {
    e.preventDefault()
    if (!tryAcquire()) return
    saveSettings({
      operating_hours: hours.trim(),
      is_temporarily_closed: closed,
      closed_reason: closed ? reason.trim() : null,
    })
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-5 max-w-lg">
      <div className="hidden md:block">
        <StaffAlertsPanel onNavigate={onAlertNavigate} />
      </div>

      <div className="md:hidden">
        <StaffPushSettingsToggle role="authority" />
      </div>

      <form onSubmit={handleSubmit} className="glass p-4 md:p-6 space-y-5 rounded-2xl">
      <div className="hidden md:block">
        <h2 className="text-lg md:text-sm font-semibold text-slate-900 dark:text-slate-100">{data?.drop_point_name}</h2>
        <p className="text-sm md:text-xs text-slate-500 mt-1">Operating hours and closure status</p>
      </div>

      <div>
        <label className="label">Operating hours</label>
        <input
          type="text"
          className="input-field w-full"
          value={hours}
          onChange={(e) => setHours(e.target.value)}
          placeholder="Mon-Fri 08:00-17:00"
          required
        />
      </div>

      <label className="flex items-center gap-3 cursor-pointer">
        <input
          type="checkbox"
          checked={closed}
          onChange={(e) => setClosed(e.target.checked)}
          className="rounded border-slate-600"
        />
        <span className="text-sm text-slate-700 dark:text-slate-300">Temporarily closed</span>
      </label>

      {closed && (
        <div>
          <label className="label">Closure reason</label>
          <textarea
            className="input-field w-full min-h-[80px]"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="e.g. Renovation until Monday"
            required
          />
        </div>
      )}

      <SubmitButton loading={isSubmitting} className="btn-primary w-full md:w-auto min-h-[48px] text-base md:text-sm">
        Save settings
      </SubmitButton>

      <div className="hidden md:block pt-4 border-t border-slate-200 dark:border-slate-800">
        <StaffPushSettingsToggle role="authority" />
      </div>
    </form>
    </div>
  )
}

function TabBadge({ count }) {
  if (!count || count < 1) return null
  return (
    <span className="ml-1.5 inline-flex items-center justify-center min-w-[18px] h-[18px]
                     px-1 text-[10px] font-bold rounded-full bg-red-600 text-white">
      {count > 99 ? '99+' : count}
    </span>
  )
}

function AuthorityDashboardContent() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { authority, logout } = useAuthorityAuth()
  const openLightbox = useAuthorityLightbox()
  const [tab, setTab] = useState('incoming')
  const [claimsHighlightId, setClaimsHighlightId] = useState(null)
  const [showScanner, setShowScanner] = useState(false)
  const [confirmingId, setConfirmingId] = useState(null)
  const [acknowledgedIncomingCount, setAcknowledgedIncomingCount] = useState(0)
  const [acknowledgedClaimsPending, setAcknowledgedClaimsPending] = useState(0)
  const [detailItem, setDetailItem] = useState(null)

  const incomingQuery = useQuery({
    queryKey: ['authority-incoming'],
    queryFn: getAuthorityIncoming,
    refetchInterval: 30_000,
  })

  const claimsListQuery = useQuery({
    queryKey: ['authority-claims-list'],
    queryFn: getAuthorityClaimsList,
    refetchInterval: 30_000,
  })

  const atDroppointQuery = useQuery({
    queryKey: ['authority-at-droppoint'],
    queryFn: getAuthorityAtDroppoint,
    enabled: tab === 'at-droppoint',
    refetchInterval: tab === 'at-droppoint' ? 30_000 : false,
  })

  const handoverQuery = useQuery({
    queryKey: ['authority-handover-queue'],
    queryFn: getAuthorityHandoverQueue,
    refetchInterval: 30_000,
  })

  const alertsSummaryQuery = useQuery({
    queryKey: ['authority-alerts-summary'],
    queryFn: () => getAuthorityAlerts({ limit: 1 }),
    staleTime: 30_000,
    refetchInterval: 60_000,
  })

  const incomingItems = incomingQuery.data?.items || []
  const atDroppointItems = atDroppointQuery.data?.items || []
  const handoverBadge = (handoverQuery.data?.items || []).filter((i) => i.queue_status !== 'completed').length
  const settingsBadge = alertsSummaryQuery.data?.unread_count ?? 0

  const unconfirmedIncomingCount = useMemo(
    () => incomingItems.filter((item) => !item.authority_received_at).length,
    [incomingItems],
  )

  const pendingClaimsCount = useMemo(
    () => (claimsListQuery.data?.items || []).reduce((sum, item) => sum + (item.pending_count || 0), 0),
    [claimsListQuery.data?.items],
  )

  const incomingBadge = Math.max(0, unconfirmedIncomingCount - acknowledgedIncomingCount)
  const claimsBadge = Math.max(0, pendingClaimsCount - acknowledgedClaimsPending)

  useEffect(() => {
    if (tab === 'incoming') {
      setAcknowledgedIncomingCount(unconfirmedIncomingCount)
    }
  }, [tab, unconfirmedIncomingCount])

  useEffect(() => {
    if (tab === 'claims') {
      setAcknowledgedClaimsPending(pendingClaimsCount)
    }
  }, [tab, pendingClaimsCount])

  const refreshLists = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['authority-incoming'] })
    queryClient.invalidateQueries({ queryKey: ['authority-at-droppoint'] })
  }, [queryClient])

  const handleDropoffSuccess = useCallback((data) => {
    toast.success(data.message)
    setShowScanner(false)
    setConfirmingId(null)
    invalidateAfterDropOff(queryClient, { itemId: data.item?.id })
    refreshLists()
  }, [queryClient, refreshLists])

  const confirmMutation = useMutation({
    mutationFn: confirmAuthorityDropoff,
    onSuccess: handleDropoffSuccess,
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Could not confirm drop-off')
      setConfirmingId(null)
    },
  })

  const scanMutation = useMutation({
    mutationFn: scanAuthorityQr,
    onSuccess: handleDropoffSuccess,
    onError: (err) => toast.error(err.response?.data?.detail || 'Invalid QR code'),
  })

  function handleConfirm(itemId) {
    setConfirmingId(itemId)
    confirmMutation.mutate(itemId)
  }

  const handleScan = useCallback((token) => {
    scanMutation.mutate(token)
  }, [scanMutation])

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

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

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100 text-base leading-relaxed">
      {/* Desktop header + tabs */}
      <header className="hidden md:block border-b border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-950/90 sticky top-0 z-40">
        <div className="max-w-4xl mx-auto px-4 py-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-bold">Authority Dashboard</h1>
            <p className="text-xs text-slate-400">
              {authority?.drop_point_name}
              {authority?.email && (
                <span className="text-slate-500"> · {authority.email}</span>
              )}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <ThemeToggleButton />
            <AuthorityAlertsBell onNavigate={handleAlertNavigate} />
            {tab === 'incoming' && (
              <button
                type="button"
                onClick={() => setShowScanner(true)}
                className="btn-primary text-xs px-3 py-2"
              >
                Scan QR
              </button>
            )}
            <button
              type="button"
              onClick={handleLogout}
              className="text-xs text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
            >
              Sign out
            </button>
          </div>
        </div>

        <nav className="max-w-4xl mx-auto px-4 flex gap-1 overflow-x-auto pb-0">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={`text-xs font-medium px-3 py-2.5 border-b-2 whitespace-nowrap transition-colors
                ${tab === t.id
                  ? 'border-brand-500 text-brand-600 dark:text-brand-300'
                  : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}
            >
              {t.label}
              {t.id === 'incoming' && <TabBadge count={incomingBadge} />}
              {t.id === 'claims' && <TabBadge count={claimsBadge} />}
            </button>
          ))}
        </nav>
      </header>

      {/* Mobile header */}
      <header className="md:hidden border-b border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-950/95 sticky top-0 z-40">
        <div className="px-4 py-3 flex items-center justify-between gap-2">
          <div className="min-w-0">
            <h1 className="text-lg font-bold truncate text-slate-900 dark:text-slate-100">
              {authority?.drop_point_name || 'Authority'}
            </h1>
            <p className="text-sm text-slate-500 truncate">{authority?.email}</p>
          </div>
          <div className="flex items-center gap-1 shrink-0">
            <ThemeToggleButton />
            <AuthorityAlertsBell onNavigate={handleAlertNavigate} />
            {tab === 'incoming' && (
              <button
                type="button"
                onClick={() => setShowScanner(true)}
                className="w-11 h-11 flex items-center justify-center rounded-xl text-brand-400
                           hover:bg-slate-800"
                aria-label="Scan QR code"
              >
                <QrCode className="w-5 h-5" strokeWidth={1.75} aria-hidden />
              </button>
            )}
            <button
              type="button"
              onClick={handleLogout}
              className="text-sm text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 px-2 min-h-[44px]"
            >
              Out
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-4 md:py-6 space-y-4
                       pb-[calc(5rem+env(safe-area-inset-bottom))] md:pb-8 overflow-x-hidden">
        {tab === 'incoming' && (
          <>
            {incomingQuery.isLoading && (
              <div className="flex justify-center py-16">
                <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
              </div>
            )}
            {!incomingQuery.isLoading && incomingItems.length === 0 && (
              <div className="glass p-8 text-center rounded-2xl">
                <p className="text-base text-slate-400">No incoming items right now.</p>
              </div>
            )}
            {incomingItems.map((item) => (
              <div key={item.id}>
                <StaffIncomingMobileCard
                  item={item}
                  onOpenDetail={setDetailItem}
                  onPrimaryAction={item.can_authority_confirm ? () => handleConfirm(item.id) : null}
                  primaryLabel="Confirm received"
                  primaryLoading={confirmingId === item.id}
                  onImageOpen={openLightbox}
                />
                <IncomingItemCard
                  item={item}
                  onConfirm={handleConfirm}
                  confirmingId={confirmingId}
                  onImageOpen={openLightbox}
                  onOpenDetail={setDetailItem}
                />
              </div>
            ))}
          </>
        )}

        {tab === 'at-droppoint' && (
          <>
            {atDroppointQuery.isLoading && (
              <div className="flex justify-center py-16">
                <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
              </div>
            )}
            {!atDroppointQuery.isLoading && atDroppointItems.length === 0 && (
              <div className="glass p-8 text-center rounded-2xl">
                <p className="text-base text-slate-400">No items awaiting claim.</p>
              </div>
            )}
            {atDroppointItems.map((item) => (
              <div key={item.id}>
                <StaffAtDroppointMobileCard
                  item={item}
                  onOpenDetail={setDetailItem}
                  onImageOpen={openLightbox}
                />
                <AtDroppointItemCard item={item} onImageOpen={openLightbox} onOpenDetail={setDetailItem} />
              </div>
            ))}
          </>
        )}

        {tab === 'claims' && (
          <AuthorityClaimsTab highlightItemId={claimsHighlightId} />
        )}

        {tab === 'handover' && <AuthorityHandoverTab />}

        {tab === 'settings' && <SettingsTab onAlertNavigate={handleAlertNavigate} />}
      </main>

      <p className="hidden md:block text-center text-xs text-slate-600 pb-8">
        <Link to="/" className="hover:text-slate-400">← Back to FAiND</Link>
      </p>

      <StaffBottomNav
        items={AUTHORITY_NAV}
        activeId={tab}
        onChange={setTab}
        badges={{
          incoming: incomingBadge,
          'at-droppoint': atDroppointItems.length,
          claims: claimsBadge,
          handover: handoverBadge,
          settings: settingsBadge,
        }}
      />

      <StaffMobileBottomSheet
        open={Boolean(detailItem)}
        onClose={() => setDetailItem(null)}
        title={detailItem ? getCategoryLabel(detailItem.category) : ''}
      >
        {detailItem && (
          <div className="space-y-4">
            <div className="flex items-start gap-3">
              <div className="w-12 h-12 rounded-xl bg-slate-800 flex items-center justify-center shrink-0">
                <CategoryIcon category={detailItem.category} className="w-7 h-7 text-brand-400" />
              </div>
              <div>
                <p className="text-lg font-semibold text-slate-900 dark:text-slate-100 leading-snug">
                  {detailItem.public_description}
                </p>
                <p className="text-sm text-slate-500 mt-1">{detailItem.status}</p>
              </div>
            </div>
            <p className="text-base text-slate-400 inline-flex items-center gap-2">
              <MapPin className="w-5 h-5 shrink-0" aria-hidden />
              {detailItem.location_label}
            </p>
            <p className="text-base text-slate-400 inline-flex items-center gap-2">
              <Clock className="w-5 h-5 shrink-0" aria-hidden />
              Reported {timeSincePosted(detailItem.created_at)}
            </p>
            {detailItem.tracking_reference && (
              <p className="text-sm font-mono text-slate-500">{detailItem.tracking_reference}</p>
            )}
            {detailItem.image_urls?.length > 0 && (
              <div className="flex gap-2 flex-wrap">
                {detailItem.image_urls.map((url, i) => (
                  <LightboxImage
                    key={url}
                    src={url}
                    images={detailItem.image_urls}
                    index={i}
                    onOpen={openLightbox}
                    className="w-24 h-24 rounded-xl overflow-hidden border border-slate-700"
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </StaffMobileBottomSheet>

      <StaffDesktopDetailModal
        open={Boolean(detailItem)}
        onClose={() => setDetailItem(null)}
        title={detailItem ? getCategoryLabel(detailItem.category) : ''}
        footer={detailItem?.can_authority_confirm ? (
          <button
            type="button"
            onClick={() => handleConfirm(detailItem.id)}
            disabled={confirmingId === detailItem.id}
            className="btn-primary w-full text-base min-h-[48px]"
          >
            {confirmingId === detailItem.id ? 'Confirming…' : 'Confirm received'}
          </button>
        ) : null}
      >
        {detailItem && (
          <div className="space-y-4">
            <div className="flex items-start gap-3">
              <div className="w-12 h-12 rounded-xl bg-slate-800 flex items-center justify-center shrink-0">
                <CategoryIcon category={detailItem.category} className="w-7 h-7 text-brand-400" />
              </div>
              <div>
                <p className="text-lg font-semibold text-slate-900 dark:text-slate-100 leading-snug">
                  {detailItem.public_description}
                </p>
                <p className="text-sm text-slate-500 mt-1">{detailItem.status}</p>
              </div>
            </div>
            <p className="text-base text-slate-400 inline-flex items-center gap-2">
              <MapPin className="w-5 h-5 shrink-0" aria-hidden />
              {detailItem.location_label}
            </p>
            <p className="text-base text-slate-400 inline-flex items-center gap-2">
              <Clock className="w-5 h-5 shrink-0" aria-hidden />
              Reported {timeSincePosted(detailItem.created_at)}
            </p>
            {detailItem.tracking_reference && (
              <p className="text-sm font-mono text-slate-500">{detailItem.tracking_reference}</p>
            )}
            {detailItem.image_urls?.length > 0 && (
              <div className="flex gap-2 flex-wrap">
                {detailItem.image_urls.map((url, i) => (
                  <LightboxImage
                    key={url}
                    src={url}
                    images={detailItem.image_urls}
                    index={i}
                    onOpen={openLightbox}
                    className="w-24 h-24 rounded-xl overflow-hidden border border-slate-700"
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </StaffDesktopDetailModal>

      {showScanner && (
        <AuthorityQrScanner
          onScan={handleScan}
          onClose={() => setShowScanner(false)}
        />
      )}

      <AuthorityPushPromptTrigger />
      <StaffPushPromptBanner role="authority" enabled />
    </div>
  )
}

export default function AuthorityDashboardPage() {
  return (
    <AuthorityLightboxProvider>
      <AuthorityDashboardContent />
    </AuthorityLightboxProvider>
  )
}
