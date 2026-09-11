/**
 * Mounts global chat WebSockets while the user is logged in (any page).
 */
import { useInboxChatSockets } from '../hooks/useInboxChatSockets'

export default function ChatRealtimeBridge() {
  useInboxChatSockets()
  return null
}
