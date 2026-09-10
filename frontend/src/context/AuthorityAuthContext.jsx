import React, { createContext, useContext, useState, useCallback, useEffect } from 'react'
import {
  setAuthorityAccessToken,
  clearAuthorityAccessToken,
  setAuthoritySessionActive,
  getAuthorityAccessToken,
  getAuthorityMe,
  hasAuthoritySessionFlag,
  markAuthoritySessionExpired,
} from '../services/authorityService'

const AuthorityAuthContext = createContext(null)

export function AuthorityAuthProvider({ children }) {
  const [authority, setAuthority] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = getAuthorityAccessToken()
    if (!token) {
      setAuthoritySessionActive(false)
      setLoading(false)
      return
    }
    setAuthoritySessionActive(true)
    getAuthorityMe()
      .then((profile) => {
        setAuthority(profile)
        setAuthoritySessionActive(true)
      })
      .catch(() => {
        if (hasAuthoritySessionFlag() || getAuthorityAccessToken()) {
          markAuthoritySessionExpired()
        }
        clearAuthorityAccessToken()
        setAuthoritySessionActive(false)
        setAuthority(null)
      })
      .finally(() => setLoading(false))
  }, [])

  const completeLogin = useCallback((accessToken, profile) => {
    setAuthorityAccessToken(accessToken)
    setAuthoritySessionActive(true)
    setAuthority(profile || null)
  }, [])

  const logout = useCallback(() => {
    clearAuthorityAccessToken()
    setAuthoritySessionActive(false)
    setAuthority(null)
  }, [])

  const value = {
    authority,
    loading,
    isAuthorityAuthenticated: Boolean(authority),
    completeLogin,
    logout,
    refreshProfile: async () => {
      const profile = await getAuthorityMe()
      setAuthority(profile)
      return profile
    },
  }

  return (
    <AuthorityAuthContext.Provider value={value}>
      {children}
    </AuthorityAuthContext.Provider>
  )
}

export function useAuthorityAuth() {
  const ctx = useContext(AuthorityAuthContext)
  if (!ctx) throw new Error('useAuthorityAuth must be used inside AuthorityAuthProvider')
  return ctx
}
