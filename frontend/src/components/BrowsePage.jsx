/**
 * BrowsePage — shared layout for /lost and /found (Section 24.2).
 * Accepts `defaultType` ("lost" | "found") to pre-filter the feed.
 *
 * Features:
 *  - Search bar
 *  - Collapsible filter panel: category (multi-select), location, date range, status, sort
 *  - 20-item card grid
 *  - Load More button (offset pagination)
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import NavBar from './NavBar'
import ItemCard from './ItemCard'
import { browseItems, getPublicCampusZones } from '../services/itemService'
import { useAuth } from '../context/AuthContext'
import CategoryFilterGrid from './CategoryFilterGrid'
import {
  Search,
  PartyPopper,
  EmptyInboxIcon,
  X,
} from './icons'

const STATUSES_LOST  = [{ value: 'open', label: 'Open' }, { value: 'potential_match', label: 'Potential Match' }]
const STATUSES_FOUND = [{ value: 'found', label: 'Available' }, { value: 'potential_match', label: 'Potential Match' }]

const SORT_OPTIONS = [
  { value: 'newest',   label: 'Newest First' },
  { value: 'oldest',   label: 'Oldest First' },
  { value: 'activity', label: 'Most Recent Activity' },
]

const PAGE_SIZE = 20

function Checkbox({ checked, onChange, children }) {
  return (
    <label className="flex items-center gap-2 cursor-pointer group">
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="w-4 h-4 rounded border-slate-300 dark:border-slate-600
                   text-brand-600 focus:ring-brand-500 bg-white dark:bg-slate-700"
      />
      <span className="text-sm text-slate-700 dark:text-slate-300 group-hover:text-brand-600
                       dark:group-hover:text-brand-400 transition-colors">
        {children}
      </span>
    </label>
  )
}

export default function BrowsePage({ defaultType }) {
  const { isAuthenticated, authReady, user } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()

  // ── Filter state ────────────────────────────────────────────────────────────
  const [q,           setQ]           = useState(searchParams.get('q') || '')
  const [categories,  setCategories]  = useState(
    searchParams.getAll('category').length ? searchParams.getAll('category') : []
  )
  const [locationId,  setLocationId]  = useState('')
  const [dateFrom,    setDateFrom]    = useState('')
  const [dateTo,      setDateTo]      = useState('')
  const [statuses,    setStatuses]    = useState([])
  const [sort,        setSort]        = useState('newest')
  const [skip,        setSkip]        = useState(0)
  const [filtersOpen, setFiltersOpen] = useState(false)

  const searchRef   = useRef(null)
  const [inputQ, setInputQ] = useState(q)

  // Debounce search input
  useEffect(() => {
    const t = setTimeout(() => setQ(inputQ), 400)
    return () => clearTimeout(t)
  }, [inputQ])

  // Reset pagination when filters change
  useEffect(() => { setSkip(0) }, [q, categories, locationId, dateFrom, dateTo, statuses, sort])

  // ── Campus zones for location filter ────────────────────────────────────────
  const { data: zones = [] } = useQuery({
    queryKey: ['campus-zones-public'],
    queryFn: getPublicCampusZones,
  })

  // ── Browse query ────────────────────────────────────────────────────────────
  const queryParams = {
    item_type:   defaultType,
    category:    categories,
    location_id: locationId || null,
    date_from:   dateFrom || null,
    date_to:     dateTo   || null,
    status:      statuses,
    q,
    sort,
    skip,
    limit: PAGE_SIZE,
  }

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['browse', defaultType, isAuthenticated, queryParams],
    queryFn: () => browseItems(queryParams),
    enabled: authReady,
    keepPreviousData: true,
  })

  // ── Accumulated items for Load More ─────────────────────────────────────────
  const [allItems, setAllItems] = useState([])

  useEffect(() => {
    if (!data?.items) return
    if (skip === 0) {
      setAllItems(data.items)
    } else {
      setAllItems((prev) => {
        const ids = new Set(prev.map((i) => i.id))
        return [...prev, ...data.items.filter((i) => !ids.has(i.id))]
      })
    }
  }, [data, skip])

  function toggleCategory(val) {
    setCategories((prev) =>
      prev.includes(val) ? prev.filter((c) => c !== val) : [...prev, val]
    )
  }

  function toggleStatus(val) {
    setStatuses((prev) =>
      prev.includes(val) ? prev.filter((s) => s !== val) : [...prev, val]
    )
  }

  function clearFilters() {
    setInputQ('')
    setQ('')
    setCategories([])
    setLocationId('')
    setDateFrom('')
    setDateTo('')
    setStatuses([])
    setSort('newest')
  }

  const hasFilters = q || categories.length || locationId || dateFrom || dateTo || statuses.length

  const TitleIcon = defaultType === 'lost' ? Search : PartyPopper
  const titleText = defaultType === 'lost' ? 'Lost Items' : 'Found Items'
  const subtitle = defaultType === 'lost'
    ? 'Browse items reported lost on campus. See something you recognize?'
    : 'Browse items found on campus. Is one of these yours?'

  const statusOptions = defaultType === 'lost' ? STATUSES_LOST : STATUSES_FOUND

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 transition-colors duration-200">
      <NavBar />

      <div className="page-container py-8 max-md:py-5 max-w-6xl">
        {/* ── Page header ── */}
        <div className="mb-6 max-md:mb-4">
          <h1 className="text-2xl max-md:text-lg font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
            <TitleIcon className="w-6 h-6 max-md:w-5 max-md:h-5 text-brand-600 dark:text-brand-400" aria-hidden />
            {titleText}
          </h1>
          <p className="text-sm max-md:text-xs text-slate-500 dark:text-slate-400 mt-1">{subtitle}</p>
        </div>

        {/* ── Search + filter controls ── */}
        <div className="glass p-4 max-md:p-3 mb-6 max-md:mb-4 rounded-2xl flex flex-col gap-3 max-md:gap-2">
          {/* Search bar */}
          <div className="flex flex-col max-md:gap-2 sm:flex-row items-stretch sm:items-center gap-3">
            <div className="relative flex-1">
              <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400"
                   fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round"
                      d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
              </svg>
              <input
                ref={searchRef}
                type="text"
                value={inputQ}
                onChange={(e) => setInputQ(e.target.value)}
                placeholder={`Search ${defaultType} items…`}
                className="input-field w-full pl-9"
              />
            </div>

            {/* Sort dropdown */}
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value)}
              className="input-field w-44 max-md:w-full flex-shrink-0"
            >
              {SORT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>

            {/* Filter toggle */}
            <button
              onClick={() => setFiltersOpen((o) => !o)}
              className={`flex items-center gap-1.5 text-sm font-medium px-3 py-2 rounded-xl
                          border transition-colors duration-150 flex-shrink-0
                          ${filtersOpen || hasFilters
                            ? 'border-brand-500 text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-900/20'
                            : 'border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'}`}
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round"
                      d="M12 3c2.755 0 5.455.232 8.083.678.533.09.917.556.917 1.096v1.044a2.25 2.25 0 0 1-.659 1.591l-5.432 5.432a2.25 2.25 0 0 0-.659 1.591v2.927a2.25 2.25 0 0 1-1.244 2.013L9.75 21v-6.568a2.25 2.25 0 0 0-.659-1.591L3.659 7.409A2.25 2.25 0 0 1 3 5.818V4.774c0-.54.384-1.006.917-1.096A48.32 48.32 0 0 1 12 3Z" />
              </svg>
              Filters
              {hasFilters && (
                <span className="w-2 h-2 rounded-full bg-brand-500 inline-block" />
              )}
            </button>
          </div>

          {/* Collapsible filter panel */}
          {filtersOpen && (
            <div className="border-t border-slate-200/60 dark:border-slate-700/60 pt-4
                            grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {/* Category */}
              <div className="w-fit">
                <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">
                  Category
                </p>
                <CategoryFilterGrid selected={categories} onToggle={toggleCategory} />
              </div>

              {/* Location */}
              <div>
                <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">
                  Campus Location
                </p>
                <select
                  value={locationId}
                  onChange={(e) => setLocationId(e.target.value)}
                  className="input-field w-full"
                >
                  <option value="">All Locations</option>
                  {zones.map((z) => (
                    <option key={z.id} value={z.id}>{z.name}</option>
                  ))}
                </select>

                {/* Status filter */}
                <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mt-4 mb-2">
                  Status
                </p>
                <div className="flex flex-col gap-1.5">
                  {statusOptions.map((s) => (
                    <Checkbox
                      key={s.value}
                      checked={statuses.includes(s.value)}
                      onChange={() => toggleStatus(s.value)}
                    >
                      {s.label}
                    </Checkbox>
                  ))}
                </div>
              </div>

              {/* Date range */}
              <div className="sm:col-span-2 lg:col-span-2">
                <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">
                  Date Range ({defaultType === 'lost' ? 'Lost' : 'Found'})
                </p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-slate-500 mb-1 block">From</label>
                    <input
                      type="date"
                      value={dateFrom}
                      onChange={(e) => setDateFrom(e.target.value)}
                      className="input-field w-full"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-slate-500 mb-1 block">To</label>
                    <input
                      type="date"
                      value={dateTo}
                      onChange={(e) => setDateTo(e.target.value)}
                      className="input-field w-full"
                    />
                  </div>
                </div>

                {hasFilters && (
                  <button
                    onClick={clearFilters}
                    className="mt-4 text-sm text-red-500 hover:text-red-700 dark:hover:text-red-400
                               font-medium flex items-center gap-1 transition-colors"
                  >
                    <X className="w-4 h-4" aria-hidden />
                    Clear all filters
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        {/* ── Results ── */}
        {isLoading && skip === 0 ? (
          <div className="flex justify-center py-20">
            <div className="w-9 h-9 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : !allItems.length ? (
          <div className="flex flex-col items-center justify-center py-20 gap-3 text-center">
            <EmptyInboxIcon className="w-14 h-14 text-slate-400" />
            <p className="text-slate-500 dark:text-slate-400 text-sm max-w-xs">
              {hasFilters
                ? 'No items match your filters. Try adjusting or clearing them.'
                : `No ${defaultType} items posted yet.`}
            </p>
            {hasFilters && (
              <button onClick={clearFilters} className="btn-secondary text-sm">
                Clear Filters
              </button>
            )}
          </div>
        ) : (
          <>
            {/* Result count */}
            <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
              {isFetching && skip > 0 ? 'Loading more…' : `${data?.total ?? allItems.length} item${(data?.total ?? allItems.length) !== 1 ? 's' : ''} found`}
            </p>

            {/* Card grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 max-md:gap-2.5">
              {allItems.map((item) => (
                <ItemCard key={item.id} item={item} viewerUserId={user?.id} />
              ))}
            </div>

            {/* Load More */}
            {allItems.length < (data?.total ?? 0) && (
              <div className="flex justify-center mt-8">
                <button
                  onClick={() => setSkip((s) => s + PAGE_SIZE)}
                  disabled={isFetching}
                  className="btn-secondary px-8 py-2.5 disabled:opacity-50"
                >
                  {isFetching ? 'Loading…' : `Load More (${(data?.total ?? 0) - allItems.length} remaining)`}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
