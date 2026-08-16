import { useState, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { streamChat } from '../services/api'
import ChatWindow from '../components/ChatWindow'
import ChatInput from '../components/ChatInput'
import RecentActions from '../components/RecentActions'
import HITLConfirmModal from '../components/HITLConfirmModal'
import './CopilotPage.css'

let msgIdCounter = 1
function newId() { return msgIdCounter++ }

export default function CopilotPage() {
  const { token, user, logout } = useAuth()
  const navigate = useNavigate()

  const [messages,       setMessages]       = useState([])
  const [streaming,      setStreaming]       = useState(false)
  const [actionRefresh,  setActionRefresh]   = useState(0)
  const [sidebarOpen,    setSidebarOpen]     = useState(true)

  // HITL state
  const [hitl, setHitl] = useState(null)  // { message, pendingAction, confirmationId }
  const [hitlLoading, setHitlLoading] = useState(false)

  const abortRef = useRef(null)

  function handleLogout() {
    abortRef.current?.()
    logout()
    navigate('/login')
  }

  const sendMessage = useCallback((text) => {
    // Add user message
    const userId = newId()
    setMessages(prev => [...prev, { id: userId, role: 'user', text }])

    // Add streaming placeholder for assistant
    const assistantId = newId()
    setMessages(prev => [...prev, {
      id: assistantId,
      role: 'assistant',
      text: '',
      isStreaming: true,
      statusStages: [],
      agent: null,
    }])
    setStreaming(true)

    const abort = streamChat(text, token, {
      onStatus(payload) {
        setMessages(prev => prev.map(m =>
          m.id === assistantId
            ? { ...m, statusStages: [...(m.statusStages || []), payload] }
            : m
        ))
      },
      onDelta(payload) {
        setMessages(prev => prev.map(m =>
          m.id === assistantId
            ? { ...m, text: (m.text || '') + (payload.content || '') }
            : m
        ))
      },
      onDone(payload) {
        const data = payload.data || {}
        const answer = data.answer || ''
        const agent  = payload.agent || null

        // Check for HITL pending
        if (data.action_taken === 'PENDING_CONFIRMATION' || data.requires_confirmation) {
          setHitl({
            message:        text,
            pendingAction:  data.pending_description || data.answer || 'Confirm this action',
            confirmationId: data.confirmation_id || null,
          })
        }

        setMessages(prev => prev.map(m =>
          m.id === assistantId
            ? {
                ...m,
                isStreaming: false,
                text:        answer || m.text,
                agent:       agent,
                sqlQuery:    data.sql || null,
                sources:     data.sources || null,
              }
            : m
        ))
        setStreaming(false)

        // Refresh action log if action agent responded
        if (agent === 'action_agent') {
          setActionRefresh(r => r + 1)
        }
      },
      onError(err) {
        setMessages(prev => prev.map(m =>
          m.id === assistantId
            ? {
                ...m,
                isStreaming: false,
                text: `⚠ Error: ${err.message || 'Something went wrong. Please try again.'}`,
                agent: 'none',
              }
            : m
        ))
        setStreaming(false)
      },
    })

    abortRef.current = abort
  }, [token])

  async function handleHITLConfirm(confirmationId) {
    if (!hitl) return
    setHitlLoading(true)
    try {
      const res = await fetch('/api/v1/chat/actions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          message:         hitl.message,
          confirm:         true,
          confirmation_id: confirmationId,
        }),
      })
      const data = await res.json()
      const answer = data?.data?.answer || 'Action confirmed.'
      setMessages(prev => [...prev, {
        id:    newId(),
        role:  'assistant',
        text:  answer,
        agent: 'action_agent',
      }])
      setActionRefresh(r => r + 1)
    } catch (err) {
      setMessages(prev => [...prev, {
        id:   newId(),
        role: 'assistant',
        text: `⚠ Confirmation failed: ${err.message}`,
        agent: 'none',
      }])
    } finally {
      setHitlLoading(false)
      setHitl(null)
    }
  }

  function handleHITLDeny() {
    setHitl(null)
    setMessages(prev => [...prev, {
      id:   newId(),
      role: 'assistant',
      text: 'Action cancelled. No changes were made.',
      agent: 'none',
    }])
  }

  const roleColor = { ADMIN: 'tag-action', MANAGER: 'tag-sql', EMPLOYEE: 'tag-router' }

  return (
    <div className="copilot-root">
      {/* ---- Header ---- */}
      <header className="copilot-header glass">
        <div className="copilot-header-left">
          <span className="copilot-logo-icon">⚡</span>
          <div>
            <span className="copilot-logo-text">NovaWorks</span>
            <span className="copilot-logo-sub">PeopleOps Copilot</span>
          </div>
        </div>
        <div className="copilot-header-right">
          {user && (
            <div className="copilot-user">
              <span className={`tag ${roleColor[user.role] || 'tag-router'}`}>
                {user.role}
              </span>
              <span className="copilot-user-name">{user.full_name}</span>
            </div>
          )}
          <button
            id="sidebar-toggle-btn"
            type="button"
            className="btn btn-ghost copilot-sidebar-toggle"
            onClick={() => setSidebarOpen(s => !s)}
            title="Toggle action log"
            aria-label="Toggle recent actions sidebar"
          >
            {sidebarOpen ? '▶' : '◀'} Actions
          </button>
          <button
            id="logout-btn"
            type="button"
            className="btn btn-ghost copilot-logout"
            onClick={handleLogout}
          >
            Sign out
          </button>
        </div>
      </header>

      {/* ---- Body ---- */}
      <div className="copilot-body">
        {/* Main chat column */}
        <main className="copilot-chat-column">
          <ChatWindow messages={messages} />
          <ChatInput onSend={sendMessage} disabled={streaming} />
        </main>

        {/* Right sidebar */}
        {sidebarOpen && (
          <RecentActions token={token} refreshTrigger={actionRefresh} />
        )}
      </div>

      {/* ---- HITL Modal ---- */}
      {hitl && (
        <HITLConfirmModal
          message={hitl.message}
          pendingAction={hitl.pendingAction}
          confirmationId={hitl.confirmationId}
          onConfirm={handleHITLConfirm}
          onDeny={handleHITLDeny}
          loading={hitlLoading}
        />
      )}
    </div>
  )
}
