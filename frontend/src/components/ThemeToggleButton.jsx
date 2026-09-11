import { Moon, Sun } from 'lucide-react'
import { useTheme } from '../context/ThemeContext'

/**
 * Dark/light toggle — Sun in dark mode (switch to light), Moon in light mode.
 */
export default function ThemeToggleButton({ className = '' }) {
  const { dark, toggle } = useTheme()

  return (
    <button
      type="button"
      onClick={toggle}
      className={`w-9 h-9 rounded-xl flex items-center justify-center
                 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800
                 transition-colors duration-150 ${className}`}
      aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {dark ? <Sun className="w-5 h-5" strokeWidth={1.75} /> : <Moon className="w-5 h-5" strokeWidth={1.75} />}
    </button>
  )
}
