import { Routes, Route } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import PushPromptBanner from './components/PushPromptBanner'
import PushPromptTrigger from './components/PushPromptTrigger'
import OfflineBanner from './components/OfflineBanner'
import ChatRealtimeBridge from './components/ChatRealtimeBridge'

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
import ItemUnavailablePage from './pages/ItemUnavailablePage'
import OfflinePage from './pages/OfflinePage'
import VerifyOwnershipPage from './pages/VerifyOwnershipPage'
import IHaveThisItemPage   from './pages/IHaveThisItemPage'
import ThisMightBeMinePage  from './pages/ThisMightBeMinePage'
import MessagesPage        from './pages/MessagesPage'
import ReturnConfirmPage   from './pages/ReturnConfirmPage'
import ReturnedDetailPage  from './pages/ReturnedDetailPage'
import AdminLoginPage      from './pages/AdminLoginPage'
import AdminDashboardPage  from './pages/AdminDashboardPage'

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
      {/* Global overlays — available on every page */}
      <OfflineBanner />
      <PushPromptTrigger />
      <PushPromptBanner />
      <ChatRealtimeBridge />
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
        <Route path="/returned"    element={<ReturnedItemsPage />} />
        <Route path="/items/:itemId" element={<ItemDetailPage />} />
        <Route path="/item-unavailable" element={<ItemUnavailablePage />} />
        <Route path="/offline" element={<OfflinePage />} />

        {/* Feature I — Path A ownership verification */}
        <Route path="/verify-ownership/:matchId" element={
          <ProtectedRoute><VerifyOwnershipPage /></ProtectedRoute>
        } />

        {/* Feature J — Path B I Have This Item */}
        <Route path="/i-have-this-item/:lostItemId" element={
          <ProtectedRoute><IHaveThisItemPage /></ProtectedRoute>
        } />

        {/* Feature K — Path C This Might Be Mine */}
        <Route path="/this-might-be-mine/:foundItemId" element={
          <ProtectedRoute><ThisMightBeMinePage /></ProtectedRoute>
        } />
        <Route path="/messages" element={
          <ProtectedRoute><MessagesPage /></ProtectedRoute>
        } />
        <Route path="/messages/:conversationId" element={
          <ProtectedRoute><MessagesPage /></ProtectedRoute>
        } />

        {/* Feature M — Return confirmation */}
        <Route path="/returns/confirm/:matchId" element={
          <ProtectedRoute><ReturnConfirmPage /></ProtectedRoute>
        } />
        <Route path="/returns/:returnId" element={
          <ProtectedRoute><ReturnedDetailPage /></ProtectedRoute>
        } />

        {/* Feature R — secret admin route (404 if secret path wrong) */}
        <Route path="/admin/:adminSecret/login" element={<AdminLoginPage />} />
        <Route path="/admin/:adminSecret/dashboard" element={<AdminDashboardPage />} />
        <Route path="/admin/:adminSecret" element={<AdminLoginPage />} />

        {/* Fallback — unmatched routes show a not-found page, never silently redirect */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AuthProvider>
  )
}
