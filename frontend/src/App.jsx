import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { AuthorityAuthProvider } from './context/AuthorityAuthContext'
import { SupervisorAuthProvider } from './context/SupervisorAuthContext'
import EscrowClaimPrompt from './components/EscrowClaimPrompt'
import PushPromptBanner from './components/PushPromptBanner'
import PushPromptTrigger from './components/PushPromptTrigger'
import OfflineBanner from './components/OfflineBanner'
import { AuthoritySessionRedirect, SupervisorSessionRedirect, AdminSessionRedirect } from './components/RoleSessionRedirects'

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
import ReturnedItemsPage   from './pages/ReturnedItemsPage'
import ItemDetailPage      from './pages/ItemDetailPage'
import ItemInterestPage    from './pages/ItemInterestPage'
import ItemUnavailablePage from './pages/ItemUnavailablePage'
import OfflinePage from './pages/OfflinePage'
import ReturnConfirmPage   from './pages/ReturnConfirmPage'
import ReturnedDetailPage  from './pages/ReturnedDetailPage'
import AdminTotpPage         from './pages/AdminTotpPage'
import AuthorityOtpPage      from './pages/AuthorityOtpPage'
import AdminDashboardPage    from './pages/AdminDashboardPage'
import AuthorityDashboardPage from './pages/AuthorityDashboardPage'
import SupervisorDashboardPage from './pages/SupervisorDashboardPage'
import ClaimFormPage          from './pages/ClaimFormPage'
import ClaimStatusPage        from './pages/ClaimStatusPage'
import HandoverConfirmPage    from './pages/HandoverConfirmPage'

// Guards
import ProtectedRoute from './components/ProtectedRoute'
import AuthorityProtectedRoute from './components/AuthorityProtectedRoute'
import SupervisorProtectedRoute from './components/SupervisorProtectedRoute'
import GuestRoute     from './components/GuestRoute'
import NavBar         from './components/NavBar'
import BottomNav      from './components/BottomNav'

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
      <AuthorityAuthProvider>
      <SupervisorAuthProvider>
      {/* Global overlays — available on every page */}
      <OfflineBanner />
      <PushPromptTrigger />
      <PushPromptBanner />
      <EscrowClaimPrompt />
      <AuthoritySessionRedirect />
      <SupervisorSessionRedirect />
      <AdminSessionRedirect />
      <BottomNav />
      <Routes>
        {/* Public */}
        <Route path="/" element={<HomePage />} />
        <Route path="/profile/:username" element={<PublicProfilePage />} />

        {/* Guest-only */}
        <Route path="/login"           element={<GuestRoute><LoginPage /></GuestRoute>} />
        <Route path="/authority/otp"   element={<GuestRoute><AuthorityOtpPage /></GuestRoute>} />
        <Route path="/admin/totp"       element={<GuestRoute><AdminTotpPage /></GuestRoute>} />
        <Route path="/signup"          element={<GuestRoute><SignupPage /></GuestRoute>} />
        <Route path="/forgot-password" element={<GuestRoute><ForgotPasswordPage /></GuestRoute>} />

        {/* Verify email — accessible pre-auth */}
        <Route path="/verify-email" element={<VerifyEmailPage />} />

        {/* Protected — Feature B */}
        <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
        <Route path="/settings"  element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />

        {/* Protected — Feature C: Lost Item Reporting */}
        <Route path="/report/lost"  element={<ProtectedRoute><ReportLostPage /></ProtectedRoute>} />

        {/* Feature D / W3: Found Item Reporting — public */}
        <Route path="/report/found" element={<ReportFoundPage />} />
        <Route path="/track/found" element={<Navigate to="/found" replace />} />

        {/* Feature F — public browse pages + item detail */}
        <Route path="/lost"        element={<LostItemsPage />} />
        <Route path="/found"       element={<FoundItemsPage />} />
        <Route path="/returned"    element={<ReturnedItemsPage />} />
        <Route path="/items/:itemId/interest" element={
          <ProtectedRoute><ItemInterestPage /></ProtectedRoute>
        } />
        <Route path="/items/:itemId" element={<ItemDetailPage />} />
        <Route path="/item-unavailable" element={<ItemUnavailablePage />} />
        <Route path="/offline" element={<OfflinePage />} />

        {/* Feature M — Return confirmation */}
        <Route path="/returns/confirm/:matchId" element={
          <ProtectedRoute><ReturnConfirmPage /></ProtectedRoute>
        } />
        <Route path="/returns/:returnId" element={
          <ProtectedRoute><ReturnedDetailPage /></ProtectedRoute>
        } />

        <Route path="/claims/found/:foundItemId" element={
          <ProtectedRoute><ClaimFormPage /></ProtectedRoute>
        } />

        <Route path="/claims/status/:claimId" element={
          <ProtectedRoute><ClaimStatusPage /></ProtectedRoute>
        } />

        <Route path="/handover/:handoverId" element={
          <ProtectedRoute><HandoverConfirmPage /></ProtectedRoute>
        } />
        <Route path="/handover/:handoverId/confirm" element={
          <ProtectedRoute><HandoverConfirmPage /></ProtectedRoute>
        } />

        <Route path="/authority/login" element={<Navigate to="/login" replace />} />
        <Route path="/authority/dashboard" element={
          <AuthorityProtectedRoute><AuthorityDashboardPage /></AuthorityProtectedRoute>
        } />

        <Route path="/supervisor/login" element={<Navigate to="/login" replace />} />
        <Route path="/supervisor/dashboard" element={
          <SupervisorProtectedRoute><SupervisorDashboardPage /></SupervisorProtectedRoute>
        } />

        {/* Feature R — secret admin route (404 if secret path wrong) */}
        <Route path="/admin/:adminSecret/login" element={<Navigate to="/login" replace />} />
        <Route path="/admin/:adminSecret/dashboard" element={<AdminDashboardPage />} />
        <Route path="/admin/:adminSecret" element={<Navigate to="/login" replace />} />

        {/* Fallback — unmatched routes show a not-found page, never silently redirect */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
      </SupervisorAuthProvider>
      </AuthorityAuthProvider>
    </AuthProvider>
  )
}
