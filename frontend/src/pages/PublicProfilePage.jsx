import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { userService } from '../services/userService'
import { useAuth } from '../context/AuthContext'
import NavBar from '../components/NavBar'
import ReportModal from '../components/ReportModal'

export default function PublicProfilePage() {
  const { username } = useParams()
  const { user: me } = useAuth()
  const [reportOpen, setReportOpen] = useState(false)

  const { data: profile, isLoading, isError } = useQuery({
    queryKey: ['profile', username],
    queryFn: () => userService.getPublicProfile(username),
    retry: false,
  })

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 transition-colors duration-200">
      <NavBar />

      <div className="page-container py-8 max-w-2xl">
        {isLoading && (
          <div className="flex items-center justify-center py-24">
            <div className="w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {isError && (
          <div className="glass p-10 text-center">
            <p className="text-slate-500 dark:text-slate-400 text-sm">
              This profile doesn't exist or has been removed.
            </p>
            <Link to="/" className="btn-primary mt-4 text-sm inline-flex">Go Home</Link>
          </div>
        )}

        {profile && (
          <>
            <div className="glass p-6 mb-4 animate-slide-up">
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
                {profile.profile_photo_url ? (
                  <img
                    src={profile.profile_photo_url}
                    alt={profile.username}
                    className="w-20 h-20 rounded-2xl object-cover flex-shrink-0"
                  />
                ) : (
                  <div className="w-20 h-20 rounded-2xl bg-brand-600 flex items-center justify-center
                                  text-white text-2xl font-bold flex-shrink-0">
                    {profile.full_name.split(' ').map((n) => n[0]).slice(0, 2).join('').toUpperCase()}
                  </div>
                )}

                <div className="flex-1 min-w-0">
                  <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100 mb-1">
                    {profile.full_name}
                  </h1>
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    @{profile.username}
                  </p>
                  <div className="flex flex-wrap gap-3 mt-2">
                    <span className="text-xs text-slate-400 dark:text-slate-500 flex items-center gap-1">
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 0 0 8.716-6.747M12 21a9.004 9.004 0 0 1-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 0 1 7.843 4.582M12 3a8.997 8.997 0 0 0-7.843 4.582m15.686 0A11.953 11.953 0 0 1 12 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0 1 21 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0 1 12 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 0 1 3 12c0-1.605.42-3.113 1.157-4.418" />
                      </svg>
                      {profile.university_short_name}
                    </span>
                    <span className="text-xs text-slate-400 dark:text-slate-500 flex items-center gap-1">
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5" />
                      </svg>
                      Member since {profile.member_since}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4 mb-4">
              <div className="stat-card text-center">
                <span className="text-3xl font-bold text-slate-800 dark:text-slate-100 block">
                  {profile.items_returned_count}
                </span>
                <p className="text-sm text-slate-500 dark:text-slate-400">Items Returned</p>
              </div>
            </div>

            <div className="flex gap-3">
              {me && me.username !== profile.username && (
                <button
                  type="button"
                  className="btn-ghost text-sm text-red-600 dark:text-red-400
                             hover:bg-red-50 dark:hover:bg-red-900/20"
                  onClick={() => setReportOpen(true)}
                >
                  Report User
                </button>
              )}
              {me && me.username === profile.username && (
                <Link to="/settings" className="btn-secondary text-sm">
                  Edit Profile
                </Link>
              )}
            </div>
          </>
        )}
      </div>

      {profile && (
        <ReportModal
          open={reportOpen}
          onClose={() => setReportOpen(false)}
          type="user"
          targetId={profile.id}
          targetLabel={`@${profile.username} — ${profile.full_name}`}
        />
      )}
    </div>
  )
}
