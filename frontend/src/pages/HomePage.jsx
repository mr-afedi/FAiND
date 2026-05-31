/**
 * HomePage — Section 24.1
 * Layout (top to bottom):
 *   1. NavBar (always sticky)
 *   2. Hero — campus image + blur overlay, headline, two CTAs
 *   3. Two-column preview — 5 latest lost + 5 latest found
 *   4. Recently Returned (anonymous, Section 16.6)
 *   5. "Why FAiND" section
 *   6. Safety warning banner
 *   7. FAB — fixed bottom-right, expands to report actions
 */
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../context/AuthContext'
import NavBar from '../components/NavBar'
import ItemCard from '../components/ItemCard'
import { getHomepageData } from '../services/itemService'
import { getMyMatches } from '../services/matchService'
import { getViewerBadge } from '../utils/viewerItemBadges'
import {
  Search,
  PartyPopper,
  PackageSearch,
  EmptyInboxIcon,
  Bot,
  Lock,
  Globe,
  Zap,
  AlertTriangle,
  Plus,
} from '../components/icons'

// Multiple Unsplash URLs tried in order; falls back to a gradient if all fail
const HERO_IMAGES = [
  'https://images.unsplash.com/photo-1523050854058-8df90110c9f1?auto=format&fit=crop&w=1920&q=80',
  'https://images.unsplash.com/photo-1541339907198-e08756dedf3f?auto=format&fit=crop&w=1920&q=80',
  'https://images.unsplash.com/photo-1498243691581-b145c3f54a5a?auto=format&fit=crop&w=1920&q=80',
]

function HeroBackground() {
  const [idx, setIdx]     = useState(0)
  const [failed, setFailed] = useState(false)

  function tryNext() {
    if (idx < HERO_IMAGES.length - 1) setIdx((i) => i + 1)
    else setFailed(true)
  }

  if (failed) {
    return (
      <div className="absolute inset-0 bg-gradient-to-br
                      from-brand-900 via-slate-800 to-indigo-900" />
    )
  }

  return (
    <img
      key={idx}
      src={HERO_IMAGES[idx]}
      alt=""
      onError={tryNext}
      className="absolute inset-0 w-full h-full object-cover scale-105"
      style={{ filter: 'blur(3px)' }}
    />
  )
}

// ── FAB (Floating Action Button) ─────────────────────────────────────────────

function FAB({ isAuthenticated }) {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()

  function handleAction(path) {
    setOpen(false)
    if (isAuthenticated) {
      navigate(path)
    } else {
      navigate('/login', { state: { from: path } })
    }
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-2">
      {open && (
        <>
          <button
            onClick={() => handleAction('/report/lost')}
            className="flex items-center gap-2 bg-red-500 hover:bg-red-600 text-white
                       text-sm font-semibold px-4 py-2.5 rounded-2xl shadow-lg
                       transition-all duration-150 animate-fade-in"
          >
            <PackageSearch className="w-4 h-4 shrink-0" aria-hidden />
            Report Lost Item
          </button>
          <button
            onClick={() => handleAction('/report/found')}
            className="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white
                       text-sm font-semibold px-4 py-2.5 rounded-2xl shadow-lg
                       transition-all duration-150 animate-fade-in"
          >
            <PartyPopper className="w-4 h-4 shrink-0" aria-hidden />
            Report Found Item
          </button>
        </>
      )}
      <button
        onClick={() => setOpen((o) => !o)}
        className={`w-14 h-14 rounded-2xl shadow-xl flex items-center justify-center
                    text-white text-2xl font-bold transition-all duration-200
                    ${open
                      ? 'bg-slate-600 hover:bg-slate-700 rotate-45'
                      : 'bg-brand-600 hover:bg-brand-700'}`}
        aria-label="Report item"
      >
        <Plus className="w-6 h-6" aria-hidden />
      </button>
    </div>
  )
}

// ── Section heading ───────────────────────────────────────────────────────────

function SectionHeading({ children, linkTo, linkLabel }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <h2 className="text-lg font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
        {children}
      </h2>
      {linkTo && (
        <Link to={linkTo}
              className="text-sm font-medium text-brand-600 dark:text-brand-400
                         hover:underline flex items-center gap-1">
          {linkLabel} →
        </Link>
      )}
    </div>
  )
}

// ── Empty preview placeholder ─────────────────────────────────────────────────

function EmptyPreview({ message }) {
  return (
    <div className="flex flex-col items-center justify-center py-10 text-center gap-2
                    rounded-2xl border border-dashed border-slate-200 dark:border-slate-700">
      <EmptyInboxIcon className="w-10 h-10 text-slate-400" />
      <p className="text-sm text-slate-400 dark:text-slate-500">{message}</p>
    </div>
  )
}

// ── Recently Returned teaser (Section 16.6) ───────────────────────────────────

function RecentlyReturnedTeaser({ count }) {
  if (!count || count < 1) return null
  const countLabel = count === 1 ? '1 item' : `${count} items`
  return (
    <div className="py-8 text-center border-t border-slate-200/70 dark:border-slate-800/60">
      <p className="text-sm text-slate-600 dark:text-slate-400">
        <span className="font-medium text-emerald-700 dark:text-emerald-400">{countLabel}</span>
        {' '}successfully returned this week on GCTU campus
      </p>
      <Link
        to="/returned"
        className="inline-block mt-2 text-sm text-slate-500 dark:text-slate-400
                   hover:text-brand-600 dark:hover:text-brand-400 transition-colors"
      >
        See all returned items →
      </Link>
    </div>
  )
}

// ── Why FAiND section ─────────────────────────────────────────────────────────

const WHY_ITEMS = [
  { Icon: Bot, title: 'AI-Powered Matching', desc: 'Our system automatically matches lost and found items using descriptions, images, and location.' },
  { Icon: Lock, title: 'Secure Verification', desc: 'Hidden questions and AI scoring ensure only the true owner can claim their belongings.' },
  { Icon: Globe, title: 'Campus Community', desc: 'Built specifically for GCTU students and staff — everyone helping each other.' },
  { Icon: Zap, title: 'Fast & Easy', desc: 'Post a lost or found item in under 2 minutes. No paperwork, no queues.' },
]

function WhySection() {
  return (
    <section className="py-12 px-4">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-2xl font-bold text-center text-slate-800 dark:text-slate-100 mb-8">
          Why Choose FAiND?
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {WHY_ITEMS.map((item) => (
            <div key={item.title}
                 className="glass p-5 rounded-2xl flex flex-col gap-2 text-center hover:shadow-md transition-shadow">
              <item.Icon className="w-8 h-8 mx-auto text-brand-600 dark:text-brand-400" aria-hidden />
              <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100">{item.title}</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">{item.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

// ── Safety warning banner ─────────────────────────────────────────────────────

function SafetyBanner() {
  return (
    <div className="mx-4 mb-8 max-w-5xl lg:mx-auto px-4 py-3 rounded-2xl
                    bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/40
                    flex items-start gap-3">
      <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5 text-amber-600 dark:text-amber-400" aria-hidden />
      <p className="text-xs text-amber-800 dark:text-amber-300 leading-relaxed">
        <strong>Safety reminder:</strong> Always arrange item pick-ups in public, well-lit areas on campus.
        Never share personal financial information, passwords, or meet off-campus with strangers.
        Report suspicious behaviour to campus security or flag the post using the report button.
      </p>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function HomePage() {
  const { isAuthenticated, user } = useAuth()
  const navigate = useNavigate()

  const { data: matchData } = useQuery({
    queryKey: ['my-matches'],
    queryFn: getMyMatches,
    enabled: isAuthenticated,
  })

  const { data: homepageData, isLoading } = useQuery({
    queryKey: ['homepage', isAuthenticated],
    queryFn: getHomepageData,
    refetchInterval: 60_000,
  })

  function handleCTA(path) {
    if (isAuthenticated) {
      navigate(path)
    } else {
      navigate('/login', { state: { from: path } })
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 transition-colors duration-200">
      <NavBar />

      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden min-h-[480px] flex items-center">
        {/* Background: real image with blur; falls back to gradient if image fails */}
        <HeroBackground />
        <div className="absolute inset-0 bg-gradient-to-br from-slate-900/75 via-slate-800/65 to-brand-900/60" />

        {/* Hero content */}
        <div className="relative z-10 page-container py-20 text-center">
          <div className="inline-flex items-center gap-2 bg-white/10 backdrop-blur-sm
                          text-white/90 text-xs font-medium px-3 py-1
                          rounded-full mb-6 border border-white/20">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            Now live at GCTU
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-white
                          mb-4 leading-tight tracking-tight drop-shadow-md">
            Find what you&apos;ve lost.<br />
            <span className="text-brand-300">Return what you&apos;ve found.</span>
          </h1>

          <p className="text-base sm:text-lg text-white/80 max-w-xl mx-auto mb-10 leading-relaxed">
            FAiND is GCTU&apos;s AI-powered lost and found platform.
            Post, match, verify, and safely recover items on campus.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-4">
            <button
              onClick={() => handleCTA('/report/lost')}
              className="btn-primary px-7 py-3 text-base shadow-lg"
            >
              Report Lost Item
            </button>
            <button
              onClick={() => handleCTA('/report/found')}
              className="btn-secondary px-7 py-3 text-base shadow-lg bg-white/10
                         backdrop-blur-sm border-white/30 text-white
                         hover:bg-white/20"
            >
              Report Found Item
            </button>
          </div>
        </div>
      </section>

      {/* ── Two-column preview ───────────────────────────────────────────── */}
      <section className="py-12 px-4 max-w-7xl mx-auto">
        {isLoading ? (
          <div className="flex justify-center py-16">
            <div className="w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_2px_1fr] gap-x-12 gap-y-10">
            {/* Lost Items column */}
            <div>
              <SectionHeading linkTo="/lost" linkLabel="See All Lost Items">
                <Search className="w-5 h-5 text-brand-600 dark:text-brand-400" aria-hidden />
                Latest Lost Items
              </SectionHeading>
              {!homepageData?.latest_lost?.length ? (
                <EmptyPreview message="No lost items reported yet. Be the first to post." />
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {homepageData.latest_lost.map((item) => (
                    <ItemCard
                      key={item.id}
                      item={item}
                      viewerBadge={getViewerBadge(
                        item,
                        user?.id,
                        matchData?.matches,
                        { homepage: true },
                      )}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Vertical divider — only visible on large screens */}
            <div className="hidden lg:block self-stretch w-px bg-slate-200 dark:bg-slate-700/60 rounded-full" />

            {/* Found Items column */}
            <div>
              <SectionHeading linkTo="/found" linkLabel="See All Found Items">
                <PartyPopper className="w-5 h-5 text-brand-600 dark:text-brand-400" aria-hidden />
                Latest Found Items
              </SectionHeading>
              {!homepageData?.latest_found?.length ? (
                <EmptyPreview message="No found items posted yet. Found something? Help reunite it." />
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {homepageData.latest_found.map((item) => (
                    <ItemCard
                      key={item.id}
                      item={item}
                      viewerBadge={getViewerBadge(
                        item,
                        user?.id,
                        matchData?.matches,
                        { homepage: true },
                      )}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </section>

      {/* ── Recently Returned teaser (Section 16.6) ─────────────────────── */}
      {!isLoading && (
        <RecentlyReturnedTeaser count={homepageData?.recently_returned_count ?? 0} />
      )}

      {/* ── Why FAiND ────────────────────────────────────────────────────── */}
      <div className="bg-white dark:bg-slate-900/50 border-t border-slate-100 dark:border-slate-800/50">
        <WhySection />
      </div>

      {/* ── Safety banner ────────────────────────────────────────────────── */}
      <SafetyBanner />

      {/* ── FAB ──────────────────────────────────────────────────────────── */}
      <FAB isAuthenticated={isAuthenticated} />
    </div>
  )
}
