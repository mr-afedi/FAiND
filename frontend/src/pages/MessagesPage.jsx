/**
 * MessagesPage — inbox + real-time chat (Feature L, Section 14).
 */
import { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import NavBar from '../components/NavBar'
import {
  listConversations,
  getConversation,
  listMessages,
  sendMessage,
  markConversationRead,
} from '../services/messageService'
import { useAuth } from '../context/AuthContext'
import { CHAT_EVENT, normalizeMessage } from '../utils/chatMessage'
import { ChevronLeft, Flag, MessageCircle } from '../components/icons'
import SubmitButton from '../components/SubmitButton'
import ReportModal from '../components/ReportModal'
import { useSubmitLock } from '../hooks/useSubmitLock'

const SAFETY_TEXT =
  'Keep your conversation focused on recovering your item safely. Do not share passwords, banking details, or sensitive personal information. FAiND is not responsible for off-platform exchanges.'

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const sameDay = d.toDateString() === now.toDateString()
  if (sameDay) {
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' })
}

function UserAvatar({ user, size = 'md' }) {
  const sz = size === 'sm' ? 'w-9 h-9 text-xs' : 'w-10 h-10 text-sm'
  const initials = user?.display_name
    ? user.display_name.split(' ').map((n) => n[0]).slice(0, 2).join('').toUpperCase()
    : user?.username?.[0]?.toUpperCase() ?? '?'
  if (user?.profile_photo_url) {
    return (
      <img
        src={user.profile_photo_url}
        alt=""
        className={`${sz} rounded-full object-cover shrink-0`}
      />
    )
  }
  return (
    <div className={`${sz} rounded-full bg-brand-600 flex items-center justify-center text-white font-semibold shrink-0`}>
      {initials}
    </div>
  )
}

function SeenReceipt({ message }) {
  if (!message.is_mine) return null
  return (
    <span className="text-[10px] text-slate-400 ml-1" aria-label={message.is_seen ? 'Seen' : 'Delivered'}>
      {message.is_seen ? '✓✓' : '✓'}
    </span>
  )
}

export default function MessagesPage() {
  const { conversationId: selectedId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const userId = user?.id
  const [search, setSearch] = useState('')
  const [draft, setDraft] = useState('')
  const messagesScrollRef = useRef(null)
  const [messages, setMessages] = useState([])
  const { isSubmitting, tryAcquire, release } = useSubmitLock()
  const [reportOpen, setReportOpen] = useState(false)

  const { data: inbox, isLoading: inboxLoading } = useQuery({
    queryKey: ['conversations'],
    queryFn: listConversations,
  })

  const { data: detail } = useQuery({
    queryKey: ['conversation', selectedId],
    queryFn: () => getConversation(selectedId),
    enabled: Boolean(selectedId),
  })

  const { data: messagePage, isLoading: messagesLoading } = useQuery({
    queryKey: ['messages', selectedId],
    queryFn: () => listMessages(selectedId),
    enabled: Boolean(selectedId),
  })

  useEffect(() => {
    if (messagePage?.messages && userId) {
      setMessages(messagePage.messages.map((m) => normalizeMessage(m, userId)))
    }
  }, [messagePage, userId])

  useEffect(() => {
    if (selectedId) {
      markConversationRead(selectedId).then(() => {
        queryClient.invalidateQueries({ queryKey: ['conversations'] })
        queryClient.invalidateQueries({ queryKey: ['messages-unread-count'] })
      })
    }
  }, [selectedId, queryClient])

  useEffect(() => {
    if (!userId) return undefined

    function onChat(ev) {
      const data = ev.detail
      if (!data) return

      if (data.type === 'new_message' && data.message) {
        const msg = normalizeMessage(data.message, userId)
        if (String(msg.conversation_id) !== String(selectedId)) return
        setMessages((prev) => {
          if (prev.some((m) => String(m.id) === String(msg.id))) return prev
          return [...prev, msg]
        })
      }

      if (data.type === 'messages_read' && data.message_ids?.length) {
        const ids = new Set(data.message_ids.map(String))
        setMessages((prev) =>
          prev.map((m) =>
            ids.has(String(m.id)) && m.is_mine
              ? { ...m, is_seen: true, read_at: data.read_at || m.read_at }
              : m,
          ),
        )
      }
    }

    window.addEventListener(CHAT_EVENT, onChat)
    return () => window.removeEventListener(CHAT_EVENT, onChat)
  }, [selectedId, userId])

  const sendMutation = useMutation({
    mutationFn: (body) => sendMessage(selectedId, body),
    onSuccess: (msg) => {
      const normalized = userId ? normalizeMessage(msg, userId) : msg
      setMessages((prev) => {
        if (prev.some((m) => String(m.id) === String(normalized.id))) return prev
        return [...prev, normalized]
      })
      setDraft('')
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
      queryClient.invalidateQueries({ queryKey: ['messages-unread-count'] })
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Failed to send message')
    },
    onSettled: () => {
      release()
    },
  })

  useEffect(() => {
    const el = messagesScrollRef.current
    if (el) {
      el.scrollTop = el.scrollHeight
    }
  }, [messages])

  const filtered = useMemo(() => {
    const list = inbox?.conversations ?? []
    const q = search.trim().toLowerCase()
    if (!q) return list
    return list.filter(
      (c) =>
        c.other_user.display_name.toLowerCase().includes(q)
        || c.other_user.username.toLowerCase().includes(q)
        || c.item.item_label.toLowerCase().includes(q),
    )
  }, [inbox, search])

  function handleSend(e) {
    e.preventDefault()
    const body = draft.trim()
    if (!body || !detail?.can_send) return
    if (!tryAcquire()) return
    sendMutation.mutate(body)
  }

  const sendBusy = isSubmitting || sendMutation.isPending

  const showListOnMobile = !selectedId
  const showChatOnMobile = Boolean(selectedId)
  const mobileChatOpen = showChatOnMobile

  // Keep chat chrome visible when the mobile keyboard opens (visual viewport shrinks).
  const [mobileShellHeight, setMobileShellHeight] = useState(null)

  useEffect(() => {
    if (!mobileChatOpen || typeof window === 'undefined') {
      setMobileShellHeight(null)
      return undefined
    }

    const vv = window.visualViewport
    if (!vv) return undefined

    function syncHeight() {
      setMobileShellHeight(vv.height)
    }

    syncHeight()
    vv.addEventListener('resize', syncHeight)
    vv.addEventListener('scroll', syncHeight)
    return () => {
      vv.removeEventListener('resize', syncHeight)
      vv.removeEventListener('scroll', syncHeight)
    }
  }, [mobileChatOpen])

  return (
    <div
      className={`bg-slate-50 dark:bg-slate-950 flex flex-col overflow-hidden
                  ${mobileChatOpen ? 'max-md:fixed max-md:inset-x-0 max-md:top-0 max-md:z-30' : 'h-[100dvh] md:h-screen'}`}
      style={mobileChatOpen && mobileShellHeight
        ? { height: mobileShellHeight }
        : mobileChatOpen
          ? { height: '100dvh' }
          : undefined}
    >
      <NavBar />
      <div className={`flex-1 flex flex-col min-h-0 max-w-6xl w-full mx-auto overflow-hidden
                       ${mobileChatOpen ? 'max-md:px-0 max-md:py-0' : 'page-container py-4 max-md:py-0'}`}>
        <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100 mb-4 hidden lg:block shrink-0">
          Messages
        </h1>

        <div className={`flex flex-1 min-h-0 gap-4 max-md:gap-0 overflow-hidden
                        ${mobileChatOpen
                          ? 'max-md:rounded-none max-md:border-0 max-md:shadow-none max-md:bg-transparent'
                          : 'rounded-2xl border border-slate-200/80 dark:border-slate-700/50 bg-white/80 dark:bg-slate-900/40 shadow-sm'}`}>
          {/* Inbox list */}
          <aside
            className={`flex flex-col min-h-0 w-full lg:w-80 lg:shrink-0 border-r border-slate-200/80 dark:border-slate-700/50 overflow-hidden
                        ${showListOnMobile ? 'flex' : 'hidden'} lg:flex`}
          >
            <div className="p-3 border-b border-slate-200/80 dark:border-slate-700/50 shrink-0">
              <input
                type="search"
                placeholder="Search by name or item…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="input-field text-sm"
              />
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto overscroll-y-contain">
              {inboxLoading && (
                <p className="text-sm text-slate-400 p-4 text-center">Loading…</p>
              )}
              {!inboxLoading && filtered.length === 0 && (
                <div className="p-8 text-center text-slate-400">
                  <MessageCircle className="w-10 h-10 mx-auto mb-2 opacity-50" aria-hidden />
                  <p className="text-sm">No conversations yet</p>
                  <p className="text-xs mt-1">Chat unlocks after ownership verification</p>
                </div>
              )}
              {filtered.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => navigate(`/messages/${c.id}`)}
                  className={`w-full flex items-start gap-3 p-3 text-left hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-colors
                              ${String(c.id) === String(selectedId) ? 'bg-brand-50 dark:bg-brand-900/20' : ''}`}
                >
                  <UserAvatar user={c.other_user} size="sm" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">
                        {c.other_user.display_name}
                      </span>
                      {c.last_message_at && (
                        <span className="text-[10px] text-slate-400 shrink-0">
                          {formatTime(c.last_message_at)}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-500 truncate">{c.item.item_label}</p>
                    {c.last_message_preview && (
                      <p className="text-xs text-slate-400 truncate mt-0.5">{c.last_message_preview}</p>
                    )}
                  </div>
                  {c.unread_count > 0 && (
                    <span className="shrink-0 min-w-[1.25rem] h-5 px-1 rounded-full bg-brand-600 text-white text-[10px] font-bold flex items-center justify-center">
                      {c.unread_count > 9 ? '9+' : c.unread_count}
                    </span>
                  )}
                </button>
              ))}
            </div>
          </aside>

          {/* Chat panel */}
          <section
            className={`flex-1 flex flex-col min-w-0 min-h-0 overflow-hidden
                        ${showChatOnMobile ? 'flex' : 'hidden'} lg:flex
                        ${mobileChatOpen ? 'max-md:bg-white max-md:dark:bg-slate-950' : ''}`}
          >
            {!selectedId && (
              <div className="flex-1 flex items-center justify-center text-slate-400 text-sm p-8">
                Select a conversation to start chatting
              </div>
            )}

            {selectedId && detail && (
              <>
                <header className="flex items-center gap-2 p-3 border-b border-slate-200/80 dark:border-slate-700/50 shrink-0
                                       max-md:bg-white max-md:dark:bg-slate-950 max-md:relative max-md:z-10">
                  <button
                    type="button"
                    onClick={() => navigate('/messages')}
                    className="lg:hidden p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
                    aria-label="Back to conversations"
                  >
                    <ChevronLeft className="w-5 h-5" aria-hidden />
                  </button>
                  <Link to={`/profile/${detail.other_user.username}`} className="flex items-center gap-2 flex-1 min-w-0">
                    <UserAvatar user={detail.other_user} />
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">
                        {detail.other_user.display_name}
                      </p>
                      <p className="text-xs text-slate-400 truncate">@{detail.other_user.username}</p>
                    </div>
                  </Link>
                  <Link
                    to={`/items/${detail.item.lost_item_id}`}
                    className="hidden sm:block text-xs text-brand-600 dark:text-brand-400 hover:underline truncate max-w-[140px]"
                  >
                    {detail.item.item_label}
                  </Link>
                  <button
                    type="button"
                    onClick={() => setReportOpen(true)}
                    className="p-2 rounded-lg text-slate-400 hover:text-red-500 hover:bg-slate-100 dark:hover:bg-slate-800"
                    aria-label="Report user"
                  >
                    <Flag className="w-4 h-4" aria-hidden />
                  </button>
                </header>

                <div className="px-3 py-2 bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200/60 dark:border-amber-800/40 shrink-0
                                max-md:relative max-md:z-10">
                  <p className="text-xs text-amber-900 dark:text-amber-200 leading-relaxed max-md:line-clamp-2">
                    {SAFETY_TEXT}
                  </p>
                </div>

                <div
                  ref={messagesScrollRef}
                  className="flex-1 min-h-0 overflow-y-auto overscroll-y-contain p-4 space-y-3"
                >
                  {messagesLoading && (
                    <p className="text-center text-sm text-slate-400">Loading messages…</p>
                  )}
                  {messages.map((m) => (
                    <div
                      key={m.id}
                      className={`flex ${m.is_mine ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-[85%] sm:max-w-[70%] rounded-2xl px-4 py-2 text-sm
                          ${m.is_mine
                            ? 'bg-brand-600 text-white rounded-br-md'
                            : 'bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-100 rounded-bl-md'}`}
                      >
                        <p className="whitespace-pre-wrap break-words">{m.body}</p>
                        <div className={`flex items-center justify-end gap-0.5 mt-1 text-[10px]
                          ${m.is_mine ? 'text-brand-200' : 'text-slate-400'}`}>
                          <span>{formatTime(m.created_at)}</span>
                          <SeenReceipt message={m} />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {detail.is_frozen || !detail.can_send ? (
                  <div className="p-4 border-t border-slate-200/80 dark:border-slate-700/50 bg-slate-50 dark:bg-slate-800/40 shrink-0">
                    <p className="text-sm text-center text-slate-600 dark:text-slate-400">
                      {detail.frozen_message || 'This conversation is currently paused pending a platform review.'}
                    </p>
                  </div>
                ) : (
                  <form
                    onSubmit={handleSend}
                    className="p-3 border-t border-slate-200/80 dark:border-slate-700/50 flex gap-2 shrink-0
                               max-md:bg-white max-md:dark:bg-slate-950 max-md:relative max-md:z-10
                               max-md:pb-[max(0.75rem,env(safe-area-inset-bottom))]"
                  >
                    <input
                      type="text"
                      value={draft}
                      onChange={(e) => setDraft(e.target.value)}
                      placeholder="Type a message…"
                      maxLength={2000}
                      className="input-field flex-1 text-sm"
                      disabled={sendBusy}
                    />
                    <SubmitButton
                      loading={sendBusy}
                      disabled={!draft.trim()}
                      className="btn-primary px-5 py-2 text-sm font-semibold disabled:opacity-50"
                      loadingLabel="Sending…"
                    >
                      Send
                    </SubmitButton>
                  </form>
                )}
              </>
            )}
          </section>
        </div>
      </div>

      {detail?.other_user && (
        <ReportModal
          open={reportOpen}
          onClose={() => setReportOpen(false)}
          type="user"
          targetId={detail.other_user.id}
          conversationId={selectedId}
          targetLabel={`@${detail.other_user.username}`}
        />
      )}
    </div>
  )
}
