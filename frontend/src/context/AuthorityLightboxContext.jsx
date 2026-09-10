import { createContext, useContext, useState, useCallback } from 'react'
import StaffPinchLightbox from '../components/staff-mobile/StaffPinchLightbox'

const AuthorityLightboxContext = createContext(null)

export function AuthorityLightboxProvider({ children }) {
  const [lightbox, setLightbox] = useState(null)

  const openLightbox = useCallback((images, startIdx = 0) => {
    if (!images?.length) return
    setLightbox({ images, startIdx })
  }, [])

  return (
    <AuthorityLightboxContext.Provider value={openLightbox}>
      {children}
      {lightbox && (
        <StaffPinchLightbox
          images={lightbox.images}
          startIdx={lightbox.startIdx}
          onClose={() => setLightbox(null)}
        />
      )}
    </AuthorityLightboxContext.Provider>
  )
}

export function useAuthorityLightbox() {
  const ctx = useContext(AuthorityLightboxContext)
  if (!ctx) throw new Error('useAuthorityLightbox must be used within AuthorityLightboxProvider')
  return ctx
}
