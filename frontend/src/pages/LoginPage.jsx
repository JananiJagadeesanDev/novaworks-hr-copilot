import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { apiLogin } from '../services/api'
import './LoginPage.css'

const DEMO_USERS = [
  { label: 'Admin',    email: 'admin@novaworks.com',       password: 'Admin@123' },
  { label: 'Manager',  email: 'priya.sharma@novaworks.com', password: 'Manager@123' },
  { label: 'Employee', email: 'raj.kumar@novaworks.com',    password: 'Employee@123' },
]

export default function LoginPage() {
  const { login } = useAuth()
  const navigate  = useNavigate()

  const [email,    setEmail]    = useState('admin@novaworks.com')
  const [password, setPassword] = useState('Admin@123')
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState('')

  function fillDemo(u) {
    setEmail(u.email)
    setPassword(u.password)
    setError('')
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const data = await apiLogin(email, password)
      login(data.access_token, {
        employee_id: data.employee_id,
        full_name:   data.full_name,
        role:        data.role,
      })
      navigate('/ai-copilot')
    } catch (err) {
      setError(err.message || 'Login failed. Check your credentials.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-root">
      {/* Left branding panel */}
      <div className="login-brand">
        <div className="login-brand-inner">
          <div className="login-logo">
            <span className="login-logo-icon">⚡</span>
            <span className="login-logo-text">NovaWorks</span>
          </div>
          <h1 className="login-headline">
            Your <span className="gradient-text">AI-Powered</span><br />
            HR Copilot
          </h1>
          <p className="login-sub">
            Ask anything about HR policies, query org data, or trigger
            HR workflows — all in plain language.
          </p>
          <div className="login-features">
            {[
              { icon: '📋', text: 'Policy RAG — instant policy answers' },
              { icon: '🔍', text: 'SQL Agent — natural language HR queries' },
              { icon: '⚙️', text: 'Action Agent — automated HR workflows' },
              { icon: '🔒', text: 'Role-aware, audited, and secure' },
            ].map((f, i) => (
              <div key={i} className="login-feature-item">
                <span>{f.icon}</span>
                <span>{f.text}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="login-brand-glow" />
      </div>

      {/* Right login form */}
      <div className="login-form-wrap">
        <div className="login-card glass-bright fade-in">
          <div className="login-card-header">
            <h2>Welcome back</h2>
            <p>Sign in to your NovaWorks account</p>
          </div>

          {/* Demo quick-fill buttons */}
          <div className="login-demo-row">
            <span className="login-demo-label">Quick demo:</span>
            {DEMO_USERS.map(u => (
              <button
                key={u.label}
                type="button"
                className={`login-demo-btn ${email === u.email ? 'active' : ''}`}
                onClick={() => fillDemo(u)}
              >
                {u.label}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="login-form" id="login-form">
            <div className="login-field">
              <label htmlFor="login-email">Email address</label>
              <input
                id="login-email"
                type="email"
                autoComplete="email"
                placeholder="you@novaworks.com"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="login-field">
              <label htmlFor="login-password">Password</label>
              <input
                id="login-password"
                type="password"
                autoComplete="current-password"
                placeholder="••••••••"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
              />
            </div>

            {error && (
              <div className="login-error" role="alert">
                ⚠ {error}
              </div>
            )}

            <button
              id="login-submit"
              type="submit"
              className="btn btn-primary login-submit-btn"
              disabled={loading}
            >
              {loading ? <><span className="spinner" /> Signing in…</> : 'Sign in →'}
            </button>
          </form>

          <p className="login-footer-note">
            NovaWorks PeopleOps Copilot &middot; Capstone Project
          </p>
        </div>
      </div>
    </div>
  )
}
