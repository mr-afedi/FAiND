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

const CATEGORY_ICONS = {
  electronics: '📱', bag: '🎒', id_card: '🪪', keys: '🔑',
  clothing: '👕', books_notes: '📚', wallet: '👜', jewellery: '💍', other: '📦',
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
            <span>😢</span> Report Lost Item
          </button>
          <button
            onClick={() => handleAction('/report/found')}
            className="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white
                       text-sm font-semibold px-4 py-2.5 rounded-2xl shadow-lg
                       transition-all duration-150 animate-fade-in"
          >
            <span>🎉</span> Report Found Item
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
        +
      </button>
    </div>
  )
}

// ── Section heading ───────────────────────────────────────────────────────────

function SectionHeading({ title, linkTo, linkLabel }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <h2 className="text-lg font-bold text-slate-800 dark:text-slate-100">{title}</h2>
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
      <span className="text-3xl">📭</span>
      <p className="text-sm text-slate-400 dark:text-slate-500">{message}</p>
    </div>
  )
}

// ── Recently Returned card (Section 16.6 — anonymous, no names/images) ───────

function ReturnedCard({ item }) {
  const icon = CATEGORY_ICONS[item.category] ?? '📦'
  const label = item.category.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
  const date = new Date(item.returned_at).toLocaleDateString()
  return (
    <div className="flex items-center gap-3 p-3 rounded-xl
                    bg-white dark:bg-slate-800/60 border border-slate-200/70
                    dark:border-slate-700/50">
      <div className="w-10 h-10 rounded-xl bg-green-100 dark:bg-green-900/30
                      flex items-center justify-center text-xl flex-shrink-0">
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-sm font-medium text-slate-700 dark:text-slate-300 truncate">{label}</p>
        <p className="text-xs text-slate-400 dark:text-slate-500">{date}</p>
      </div>
      <span className="ml-auto flex-shrink-0 text-[10px] font-semibold px-2 py-0.5 rounded-full
                       bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
        Returned ✓
      </span>
    </div>
  )
}

// ── Why FAiND section ─────────────────────────────────────────────────────────

const WHY_ITEMS = [
  { icon: '🤖', title: 'AI-Powered Matching',    desc: 'Our system automatically matches lost and found items using descriptions, images, and location.' },
  { icon: '🔐', title: 'Secure Verification',    desc: 'Hidden questions and AI scoring ensure only the true owner can claim their belongings.' },
  { icon: '🌍', title: 'Campus Community',        desc: 'Built specifically for GCTU students and staff — everyone helping each other.' },
  { icon: '⚡', title: 'Fast & Easy',             desc: 'Post a lost or found item in under 2 minutes. No paperwork, no queues.' },
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
              <span className="text-3xl">{item.icon}</span>
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
      <span className="text-xl flex-shrink-0 mt-0.5">⚠️</span>
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
  const { isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const { data: homepageData, isLoading } = useQuery({
    queryKey: ['homepage', isAuthenticated],
    queryFn: getHomepageData,
    staleTime: 30_000,
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
              <SectionHeading title="🔍 Latest Lost Items" linkTo="/lost" linkLabel="See All Lost Items" />
              {!homepageData?.latest_lost?.length ? (
                <EmptyPreview message="No lost items reported yet. Be the first to post." />
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {homepageData.latest_lost.map((item) => (
                    <ItemCard key={item.id} item={item} />
                  ))}
                </div>
              )}
            </div>

            {/* Vertical divider — only visible on large screens */}
            <div className="hidden lg:block self-stretch w-px bg-slate-200 dark:bg-slate-700/60 rounded-full" />

            {/* Found Items column */}
            <div>
              <SectionHeading title="🎉 Latest Found Items" linkTo="/found" linkLabel="See All Found Items" />
              {!homepageData?.latest_found?.length ? (
                <EmptyPreview message="No found items posted yet. Found something? Help reunite it." />
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {homepageData.latest_found.map((item) => (
                    <ItemCard key={item.id} item={item} />
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </section>

      {/* ── Recently Returned (Section 16.6 — anonymous) ────────────────── */}
      {homepageData?.recently_returned?.length > 0 && (
        <section className="page-container pb-12 max-w-5xl">
          <SectionHeading title="✅ Recently Returned" />
          <p className="text-xs text-slate-400 dark:text-slate-500 mb-4">
            Items successfully reunited with their owners in the past 7 days — names hidden to protect privacy.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {homepageData.recently_returned.map((item) => (
              <ReturnedCard key={item.id} item={item} />
            ))}
          </div>
        </section>
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
