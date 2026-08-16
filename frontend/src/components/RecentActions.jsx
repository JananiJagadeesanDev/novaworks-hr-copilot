import { useEffect, useState } from 'react'
import { apiGetAuditLogs } from '../services/api'
import './RecentActions.css'

const ACTION_ICONS = {
  approve_leave:         { icon: '✅', color: 'var(--clr-success)' },
  reject_leave:          { icon: '❌', color: 'var(--clr-danger)' },
  create_leave_request:  { icon: '📅', color: 'var(--clr-accent)' },
  create_announcement:   { icon: '📢', color: 'var(--clr-warning)' },
  assign_project:        { icon: '🗂️', color: 'var(--clr-info)' },
  deactivate_employee:   { icon: '🔒', color: 'var(--clr-danger)' },
  create_ticket:         { icon: '🎫', color: 'var(--clr-primary)' },
}

function getActionMeta(actionTaken) {
  if (!actionTaken) return null
  const key = Object.keys(ACTION_ICONS).find(k =>
    actionTaken.toLowerCase().includes(k.replace('_', ' ')) ||
    actionTaken.toLowerCase().includes(k)
  )
  return ACTION_ICONS[key] || { icon: '⚙️', color: 'var(--clr-primary)' }
}

function timeAgo(ts) {
  if (!ts) return ''
  const diff = (Date.now() - new Date(ts)) / 1000
  if (diff < 60)  return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

/**
 * RecentActions — sidebar panel showing HR Action Agent audit logs
 *
 * Props:
 *   token          — JWT for API calls
 *   refreshTrigger — increment to force refresh
 */
export default function RecentActions({ token, refreshTrigger }) {
  const [logs, setLogs]       = useState([])
  const [loading, setLoading] = useState(false)

  async function fetchLogs() {
    if (!token) return
    setLoading(true)
    try {
      const data = await apiGetAuditLogs(token, 15)
      // Filter to action agent only
      const actionLogs = Array.isArray(data)
        ? data.filter(l => l.agent_type === 'HR_ACTION' || l.agent_type === 'hr_action')
        : []
      setLogs(actionLogs)
    } catch {
      setLogs([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchLogs() }, [token, refreshTrigger])

  return (
    <aside className="recent-actions">
      <div className="recent-actions-header">
        <h3>Recent AI Actions</h3>
        <button
          type="button"
          className="btn btn-ghost recent-actions-refresh"
          onClick={fetchLogs}
          title="Refresh"
          aria-label="Refresh action log"
        >
          ↻
        </button>
      </div>

      <div className="recent-actions-list">
        {loading && (
          <div className="recent-actions-loading">
            <span className="spinner" />
            <span>Loading…</span>
          </div>
        )}

        {!loading && logs.length === 0 && (
          <div className="recent-actions-empty">
            <span>⚙️</span>
            <p>No HR actions yet.<br />Try an action command in the chat!</p>
          </div>
        )}

        {!loading && logs.map((log, i) => {
          const meta = getActionMeta(log.action_taken)
          return (
            <div key={log.id || i} className="action-item fade-in">
              <div className="action-icon" style={{ color: meta?.color }}>
                {meta?.icon || '⚙️'}
              </div>
              <div className="action-body">
                <p className="action-text">{log.action_taken || 'Action performed'}</p>
                <p className="action-query">{log.query?.slice(0, 80)}{log.query?.length > 80 ? '…' : ''}</p>
                <p className="action-time">{timeAgo(log.created_at)}</p>
              </div>
            </div>
          )
        })}
      </div>
    </aside>
  )
}
