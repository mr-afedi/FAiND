import { Routes, Route } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'

// Pages
import HomePage            from './pages/HomePage'
import LoginPage           from './pages/LoginPage'
import SignupPage          from './pages/SignupPage'
import VerifyEmailPage     from './pages/VerifyEmailPage'
import ForgotPasswordPage  from './pages/ForgotPasswordPage'
import DashboardPage       from './pages/DashboardPage'
import SettingsPage        from './pages/SettingsPage'
import PublicProfilePage   from './pages/PublicProfilePage'
import ReportLostPage      from './pages/ReportLostPage'
import ReportFoundPage     from './pages/ReportFoundPage'
import LostItemsPage       from './pages/LostItemsPage'
import FoundItemsPage      from './pages/FoundItemsPage'
import ItemDetailPage      from './pages/ItemDetailPage'

// Guards
import ProtectedRoute from './components/ProtectedRoute'
import GuestRoute     from './components/GuestRoute'
import NavBar         from './components/NavBar'

function NotFoundPage() {
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <NavBar />
      <div className="page-container py-24 text-center">
        <p className="text-6xl font-bold text-slate-200 dark:text-slate-800 mb-4">404</p>
        <h1 className="text-xl font-semibold text-slate-700 dark:text-slate-300 mb-2">
          Page not found
        </h1>
        <p className="text-sm text-slate-400 mb-8">
          This page doesn&apos;t exist yet or may be coming in a future feature.
        </p>
        <a href="/" className="btn-primary text-sm">Go Home</a>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* Public */}
        <Route path="/" element={<HomePage />} />
        <Route path="/profile/:username" element={<PublicProfilePage />} />

        {/* Guest-only */}
        <Route path="/login"           element={<GuestRoute><LoginPage /></GuestRoute>} />
        <Route path="/signup"          element={<GuestRoute><SignupPage /></GuestRoute>} />
        <Route path="/forgot-password" element={<GuestRoute><ForgotPasswordPage /></GuestRoute>} />

        {/* Verify email — accessible pre-auth */}
        <Route path="/verify-email" element={<VerifyEmailPage />} />

        {/* Protected — Feature B */}
        <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
        <Route path="/settings"  element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />

        {/* Protected — Feature C: Lost Item Reporting */}
        <Route path="/report/lost"  element={<ProtectedRoute><ReportLostPage /></ProtectedRoute>} />

        {/* Protected — Feature D: Found Item Reporting */}
        <Route path="/report/found" element={<ProtectedRoute><ReportFoundPage /></ProtectedRoute>} />

        {/* Feature F — public browse pages + item detail */}
        <Route path="/lost"        element={<LostItemsPage />} />
        <Route path="/found"       element={<FoundItemsPage />} />
        <Route path="/items/:itemId" element={<ItemDetailPage />} />

        {/* ── Future features will add routes here ── */}
        {/* <Route path="/messages" element={<ProtectedRoute><MessagesPage /></ProtectedRoute>} /> */}

        {/* Fallback — unmatched routes show a not-found page, never silently redirect */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AuthProvider>
  )
}
