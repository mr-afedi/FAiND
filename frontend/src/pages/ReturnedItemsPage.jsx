/**
 * ReturnedItemsPage — public anonymous returned feed (Section 16.6).
 */
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import NavBar from '../components/NavBar'
import { getPublicReturnedItems } from '../services/itemService'
import { CategoryIcon, getCategoryLabel, Check } from '../components/icons'

function ReturnedPublicCard({ item }) {
  const date = new Date(item.returned_at).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
  return (
    <article
      className="glass p-5 rounded-2xl flex flex-col gap-3
                 border border-teal-100/80 dark:border-teal-900/40"
    >
      <div className="flex items-start gap-3">
        <div className="w-11 h-11 rounded-xl bg-teal-50 dark:bg-teal-900/40
                        flex items-center justify-center text-teal-700 dark:text-teal-300 flex-shrink-0">
          <CategoryIcon category={item.category} className="w-5 h-5" aria-hidden />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium text-slate-400 dark:text-slate-500 uppercase tracking-wide">
            {getCategoryLabel(item.category)}
          </p>
        </div>
      </div>
      <div className="flex items-center justify-between gap-2 pt-1 border-t border-slate-200/60 dark:border-slate-700/50">
        <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full
                         bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300
                         inline-flex items-center gap-1">
          <Check className="w-3 h-3" aria-hidden />
          Successfully returned
        </span>
        <div className="text-right text-xs text-slate-500 dark:text-slate-400">
          <p>{date}</p>
          <p>{item.university_short_name}</p>
        </div>
      </div>
    </article>
  )
}

export default function ReturnedItemsPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['public-returned'],
    queryFn: () => getPublicReturnedItems({ limit: 100 }),
  })

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 transition-colors duration-200">
      <NavBar />

      <div className="page-container py-10 max-w-5xl">
        <header className="text-center mb-10">
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-800 dark:text-slate-100 mb-2">
            Recently Returned
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 max-w-lg mx-auto">
            Items successfully reunited on campus in the past 7 days. Names and photos are never
            shown to protect privacy.
          </p>
        </header>

        {isLoading && (
          <div className="flex justify-center py-20">
            <div className="w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {isError && (
          <p className="text-center text-slate-500 py-16">Could not load returned items.</p>
        )}

        {!isLoading && !isError && !data?.items?.length && (
          <p className="text-center text-slate-500 dark:text-slate-400 py-16">
            No items have been returned in the past 7 days yet.
          </p>
        )}

        {data?.items?.length > 0 && (
          <>
            <p className="text-sm text-slate-500 dark:text-slate-400 text-center mb-6">
              {data.total} item{data.total !== 1 ? 's' : ''} returned this week
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {data.items.map((item) => (
                <ReturnedPublicCard key={item.id} item={item} />
              ))}
            </div>
          </>
        )}

        <p className="text-center mt-10">
          <Link to="/" className="text-sm text-brand-600 dark:text-brand-400 hover:underline">
            ← Back to home
          </Link>
        </p>
      </div>
    </div>
  )
}
