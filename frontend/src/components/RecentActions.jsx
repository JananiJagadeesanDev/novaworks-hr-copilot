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
  // If the timestamp string does not contain a timezone indicator ('Z' or '+'), treat it as UTC
  const cleanTs = typeof ts === 'string' && !ts.endsWith('Z') && !ts.includes('+')
    ? `${ts}Z`
    : ts
  const diff = (Date.now() - new Date(cleanTs).getTime()) / 1000
  if (diff < 0 || diff < 60)   return 'just now'
  if (diff < 3600)  return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

function parseMeta(jsonStr) {
  if (!jsonStr) return {}
  try {
    return typeof jsonStr === 'string' ? JSON.parse(jsonStr) : jsonStr
  } catch {
    return {}
  }
}

/**
 * RecentActions — sidebar panel showing AI interactions, tokens & latency metrics
 */
export default function RecentActions({ token, refreshTrigger }) {
  const [logs, setLogs]       = useState([])
  const [loading, setLoading] = useState(false)

  async function fetchLogs() {
    if (!token) return
    setLoading(true)
    try {
      const data = await apiGetAuditLogs(token, 20)
      const rawList = Array.isArray(data) ? data : (data?.data || [])
      setLogs(rawList)
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
        <h3>AI Observability & Logs</h3>
        <button
          type="button"
          className="btn btn-ghost recent-actions-refresh"
          onClick={fetchLogs}
          title="Refresh metrics"
          aria-label="Refresh action log"
        >
          ↻
        </button>
      </div>

      <div className="recent-actions-list">
        {loading && (
          <div className="recent-actions-loading">
            <span className="spinner" />
            <span>Loading metrics…</span>
          </div>
        )}

        {!loading && logs.length === 0 && (
          <div className="recent-actions-empty">
            <span>📊</span>
            <p>No AI interactions logged yet.<br />Send a message to see live traces!</p>
          </div>
        )}

        {!loading && logs.map((log, i) => {
          const meta = getActionMeta(log.action_taken)
          const traceData = parseMeta(log.metadata_json)
          const latency = traceData.latency_ms != null ? `${traceData.latency_ms}ms` : null
          const tokens = traceData.tokens != null ? traceData.tokens : null
          const cost = traceData.cost_usd || null

          return (
            <div key={log.id || i} className="action-item fade-in">
              <div className="action-icon" style={{ color: meta?.color || 'var(--clr-primary)' }}>
                {meta?.icon || '⚡'}
              </div>
              <div className="action-body">
                <div className="action-title-row">
                  <span className="action-text">{log.action_taken || log.agent_type || 'AI Query'}</span>
                  <span className="action-time">{timeAgo(log.created_at)}</span>
                </div>
                <p className="action-query">{log.query?.slice(0, 75)}{log.query?.length > 75 ? '…' : ''}</p>
                
                {/* Observability Metrics (Tokens, Latency, Cost) */}
                <div className="action-metrics-row">
                  {latency && (
                    <span className="metric-chip metric-latency" title="Execution Latency">
                      ⚡ {latency}
                    </span>
                  )}
                  {tokens != null && (
                    <span className="metric-chip metric-tokens" title="Estimated Tokens">
                      🪙 {tokens} tok
                    </span>
                  )}
                  {cost && (
                    <span className="metric-chip metric-cost" title="Estimated API Cost">
                      {cost}
                    </span>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </aside>
  )
}
