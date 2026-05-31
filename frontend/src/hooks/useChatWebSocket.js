import { useEffect, useRef, useCallback } from 'react'
import { getAccessToken } from '../services/api'

function wsUrl(conversationId) {
  const token = getAccessToken()
  if (!token) return null
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/api/v1/ws/chat/${conversationId}?token=${encodeURIComponent(token)}`
}

/**
 * WebSocket for live chat + read receipts (Feature L).
 */
export function useChatWebSocket(conversationId, { onEvent, enabled = true }) {
  const wsRef = useRef(null)
  const onEventRef = useRef(onEvent)
  onEventRef.current = onEvent

  const send = useCallback((payload) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload))
    }
  }, [])

  useEffect(() => {
    if (!enabled || !conversationId) return undefined

    const url = wsUrl(conversationId)
    if (!url) return undefined

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data)
        onEventRef.current?.(data)
      } catch {
        /* ignore */
      }
    }

    ws.onopen = () => {
      ws.send(JSON.stringify({ type: 'mark_read' }))
    }

    const ping = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }))
      }
    }, 30000)

    return () => {
      clearInterval(ping)
      ws.close()
      wsRef.current = null
    }
  }, [conversationId, enabled])

  return { send }
}
