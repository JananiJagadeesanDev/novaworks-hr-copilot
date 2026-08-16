import { createContext, useContext, useState, useCallback } from 'react'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('nw_token') || null)
  const [user, setUser]   = useState(() => {
    try { return JSON.parse(localStorage.getItem('nw_user') || 'null') }
    catch { return null }
  })

  const login = useCallback((tokenVal, userObj) => {
    localStorage.setItem('nw_token', tokenVal)
    localStorage.setItem('nw_user', JSON.stringify(userObj))
    setToken(tokenVal)
    setUser(userObj)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('nw_token')
    localStorage.removeItem('nw_user')
    setToken(null)
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ token, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be inside AuthProvider')
  return ctx
}
