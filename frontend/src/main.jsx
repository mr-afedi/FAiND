import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import { registerSW } from 'virtual:pwa-register'
import App from './App'
import './index.css'
import { ThemeProvider } from './context/ThemeContext'

// Service worker — production only. In dev it caches stale bundles/API failures
// and causes flaky login / empty homepage until multiple hard refreshes.
if (import.meta.env.PROD) {
  registerSW({
    immediate: true,
    onOfflineReady() {
      console.info('[PWA] App shell cached — offline fallback available.')
    },
    onNeedRefresh() {
      console.info('[PWA] New version available — refresh to update.')
    },
  })
} else if ('serviceWorker' in navigator) {
  navigator.serviceWorker.getRegistrations().then((regs) => {
    regs.forEach((r) => r.unregister())
  })
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 0,
      retry: 1,
      refetchOnWindowFocus: true,
    },
  },
})

// StrictMode is intentionally omitted in this project.
// React 18 StrictMode double-invokes effects in dev, which fires two concurrent
// POST /auth/refresh requests. Because we use rotating refresh tokens (each token
// is single-use), the second request always fails and calls _clearSession(),
// killing the session on every page refresh during development.
ReactDOM.createRoot(document.getElementById('root')).render(
  <BrowserRouter>
    <ThemeProvider>
    <QueryClientProvider client={queryClient}>
      <App />
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            borderRadius: '12px',
            fontFamily: 'Inter, sans-serif',
            fontSize: '14px',
          },
        }}
      />
    </QueryClientProvider>
    </ThemeProvider>
  </BrowserRouter>
)
