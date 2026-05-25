/**
 * MessagesPage — placeholder until Feature L (real-time chat).
 * Shows when user arrives after successful Path A verification.
 */
import { Link, useParams } from 'react-router-dom'
import NavBar from '../components/NavBar'
import { MessageCircle } from '../components/icons'

export default function MessagesPage() {
  const { conversationId } = useParams()

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <NavBar />
      <div className="page-container py-16 max-w-lg mx-auto text-center">
        <MessageCircle className="w-14 h-14 mx-auto mb-4 text-brand-600 dark:text-brand-400" aria-hidden />
        <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100 mb-2">
          Chat Unlocked
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-2">
          Your ownership verification passed. Real-time messaging will be available in the
          next update (Feature L).
        </p>
        {conversationId && (
          <p className="text-xs text-slate-400 mb-8 font-mono">
            Conversation: {conversationId}
          </p>
        )}
        <Link to="/dashboard?tab=pending" className="btn-primary text-sm">
          Back to Dashboard
        </Link>
      </div>
    </div>
  )
}
