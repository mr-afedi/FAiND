import React, { createContext, useContext, useState, useCallback, useEffect } from 'react'
import {
  setSupervisorAccessToken,
  clearSupervisorAccessToken,
  setSupervisorSessionActive,
  getSupervisorAccessToken,
  getSupervisorMe,
} from '../services/supervisorService'

const SupervisorAuthContext = createContext(null)

export function SupervisorAuthProvider({ children }) {
  const [supervisor, setSupervisor] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = getSupervisorAccessToken()
    if (!token) {
      setSupervisorSessionActive(false)
      setLoading(false)
      return
    }
    setSupervisorSessionActive(true)
    getSupervisorMe()
      .then((profile) => {
        setSupervisor(profile)
        setSupervisorSessionActive(true)
      })
      .catch(() => {
        clearSupervisorAccessToken()
        setSupervisorSessionActive(false)
        setSupervisor(null)
      })
      .finally(() => setLoading(false))
  }, [])

  const completeLogin = useCallback((accessToken, profile) => {
    setSupervisorAccessToken(accessToken)
    setSupervisorSessionActive(true)
    setSupervisor(profile || null)
  }, [])

  const logout = useCallback(() => {
    clearSupervisorAccessToken()
    setSupervisorSessionActive(false)
    setSupervisor(null)
  }, [])

  return (
    <SupervisorAuthContext.Provider
      value={{
        supervisor,
        loading,
        isSupervisorAuthenticated: Boolean(supervisor),
        completeLogin,
        logout,
      }}
    >
      {children}
    </SupervisorAuthContext.Provider>
  )
}

export function useSupervisorAuth() {
  const ctx = useContext(SupervisorAuthContext)
  if (!ctx) throw new Error('useSupervisorAuth must be used inside SupervisorAuthProvider')
  return ctx
}
