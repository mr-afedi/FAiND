/**
 * Global inbox WebSockets — real-time badge + chat events on any page.
 */
import { useEffect, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { getAccessToken } from '../services/api'
import { listConversations } from '../services/messageService'
import { CHAT_EVENT, getActiveConversationId, isMessageMine } from '../utils/chatMessage'

function wsUrl(conversationId) {
  const token = getAccessToken()
  if (!token) return null
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/api/v1/ws/chat/${conversationId}?token=${encodeURIComponent(token)}`
}

export function useInboxChatSockets() {
  const { isAuthenticated, authReady, user } = useAuth()
  const queryClient = useQueryClient()
  const location = useLocation()
  const socketsRef = useRef(new Map())

  const { data: inbox } = useQuery({
    queryKey: ['conversations'],
    queryFn: listConversations,
    enabled: isAuthenticated && authReady,
    staleTime: 60_000,
  })

  const conversationIds = (inbox?.conversations ?? []).map((c) => String(c.id)).sort().join(',')

  useEffect(() => {
    if (!isAuthenticated || !user?.id || !conversationIds) {
      socketsRef.current.forEach((ws) => ws.close())
      socketsRef.current.clear()
      return undefined
    }

    const ids = conversationIds.split(',').filter(Boolean)
    const userId = user.id

    socketsRef.current.forEach((ws) => ws.close())
    socketsRef.current.clear()

    for (const convId of ids) {
      const url = wsUrl(convId)
      if (!url) continue

      const ws = new WebSocket(url)
      socketsRef.current.set(convId, ws)

      ws.onopen = () => {
        if (String(convId) === String(getActiveConversationId())) {
          ws.send(JSON.stringify({ type: 'mark_read' }))
        }
      }

      ws.onmessage = (ev) => {
        let data
        try {
          data = JSON.parse(ev.data)
        } catch {
          return
        }

        if (data.type === 'pong') return

        if (data.type === 'new_message' && data.message) {
          const msg = data.message
          const viewingConv = String(getActiveConversationId()) === String(msg.conversation_id)
          const fromOther = !isMessageMine(msg, userId)

          if (fromOther && !viewingConv) {
            queryClient.setQueryData(['messages-unread-count'], (prev) => {
              const n = typeof prev === 'number' ? prev : 0
              return n + 1
            })
          } else if (viewingConv) {
            queryClient.invalidateQueries({ queryKey: ['messages-unread-count'] })
          }

          queryClient.invalidateQueries({ queryKey: ['conversations'] })
          window.dispatchEvent(new CustomEvent(CHAT_EVENT, { detail: data }))
        }

        if (data.type === 'messages_read') {
          queryClient.invalidateQueries({ queryKey: ['messages-unread-count'] })
          queryClient.invalidateQueries({ queryKey: ['conversations'] })
          window.dispatchEvent(new CustomEvent(CHAT_EVENT, { detail: data }))
        }
      }
    }

    const ping = setInterval(() => {
      socketsRef.current.forEach((ws) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }))
        }
      })
    }, 30000)

    return () => {
      clearInterval(ping)
      socketsRef.current.forEach((ws) => ws.close())
      socketsRef.current.clear()
    }
  }, [isAuthenticated, user?.id, conversationIds, queryClient])

  useEffect(() => {
    if (!isAuthenticated) return
    const active = getActiveConversationId()
    if (!active) return

    const ws = socketsRef.current.get(active)
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'mark_read' }))
    }
  }, [location.pathname, isAuthenticated])
}
