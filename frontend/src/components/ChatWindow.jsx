import { useEffect, useRef } from 'react'
import './ChatWindow.css'

/**
 * ChatWindow — renders the message list
 *
 * messages: Array of {
 *   id, role: 'user'|'assistant',
 *   text, agent?, statusStages?, isStreaming?
 * }
 */
export default function ChatWindow({ messages, onSuggestionClick }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (messages.length === 0) {
    return <EmptyState onSuggestionClick={onSuggestionClick} />
  }

  return (
    <div className="chat-window" role="log" aria-live="polite" aria-label="Chat messages">
      {messages.map(msg => (
        <MessageBubble key={msg.id} msg={msg} />
      ))}
      <div ref={bottomRef} />
    </div>
  )
}

function EmptyState({ onSuggestionClick }) {
  const suggestions = [
    { icon: '📋', category: 'Policy', text: 'What is the maternity leave policy?' },
    { icon: '👥', category: 'People', text: 'Who is assigned to HR Policy Copilot?' },
    { icon: '📅', category: 'Leave', text: 'What is my leave balance?' },
    { icon: '⚡', category: 'Action', text: 'Apply for sick leave for tomorrow' },
  ]

  return (
    <div className="chat-empty fade-in">
      <div className="glean-hero-badge">
        <span className="glean-hero-sparkle">✨</span>
        <span>PeopleOps Assistant</span>
      </div>
      <h2 className="chat-empty-title">
        Search policies, people & HR actions
      </h2>
      <p className="chat-empty-sub">
        Ask anything across company policies, project allocations, leave records, or automate HR tasks.
      </p>
      <div className="chat-suggestions-grid">
        {suggestions.map((s, i) => (
          <button 
            key={i} 
            className="chat-suggestion-card"
            onClick={() => onSuggestionClick && onSuggestionClick(s.text)}
          >
            <div className="suggestion-card-header">
              <span className="suggestion-icon">{s.icon}</span>
              <span className="suggestion-category">{s.category}</span>
            </div>
            <span className="suggestion-text">{s.text}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

function getSourceInfo(msg) {
  if (msg.agent === 'sql_agent') {
    return {
      label: 'Projects & Employee Database',
      icon: '🗂️',
      steps: [
        'Understood question & intent',
        'Selected Projects & Employee database source',
        'Generated safe read-only SQL query',
        'Enforced role-based access control & row limits',
      ]
    }
  }
  if (msg.agent === 'policy_rag') {
    const sourceTitle = msg.sources?.[0]?.title || 'HR Policies'
    return {
      label: `HR Policies (${sourceTitle})`,
      icon: '📋',
      steps: [
        'Understood question & intent',
        'Retrieved verified policy chunks from Qdrant vector store',
        'Grounded response strictly on official company policies',
        'Verified answer accuracy and source citations',
      ]
    }
  }
  if (msg.agent === 'action_agent') {
    return {
      label: 'HR Operations REST API',
      icon: '⚙️',
      steps: [
        'Understood action intent & extracted parameters',
        'Validated caller permissions matrix',
        'Dispatched mutation via backend REST API tool',
        'Synthesized action confirmation',
      ]
    }
  }
  return {
    label: 'PeopleOps Knowledge Assistant',
    icon: '✨',
    steps: [
      'Understood question',
      'Routed through security guardrails',
      'Synthesized direct response',
    ]
  }
}

function MessageBubble({ msg }) {
  const isUser = msg.role === 'user'

  if (isUser) {
    return (
      <div className="message-row message-row--user fade-in">
        <div className="message-content">
          <div className="message-bubble bubble--user">
            <div className="message-text">
              {renderMessageText(msg.text)}
            </div>
          </div>
        </div>
        <div className="message-avatar message-avatar--user" aria-hidden="true">
          👤
        </div>
      </div>
    )
  }

  const sourceInfo = getSourceInfo(msg)

  return (
    <div className="message-row message-row--assistant fade-in">
      <div className="glean-card">
        {/* Glean Assistant Card Header */}
        <div className="glean-card-header">
          <span className="glean-header-icon">✨</span>
          <span className="glean-header-title">PeopleOps Copilot</span>
        </div>

        {/* Streaming Live Thinking Stage */}
        {msg.isStreaming && !msg.text && (
          <div className="glean-streaming-status">
            <span className="pulse-dot-alt">✨</span>
            <span>
              {msg.statusStages?.[msg.statusStages.length - 1]?.message || 'Searching enterprise data sources...'}
            </span>
          </div>
        )}

        {/* Main Answer Content */}
        {msg.text && (
          <div className="glean-card-content">
            {renderMessageText(msg.text)}
            {msg.isStreaming && <span className="stream-cursor" aria-hidden="true" />}
          </div>
        )}

        {/* Source Footer */}
        {!msg.isStreaming && msg.text && (
          <div className="glean-source-footer">
            <span className="glean-source-icon">{sourceInfo.icon}</span>
            <span className="glean-source-text">
              <span className="source-muted">Source:</span> {sourceInfo.label}
            </span>
          </div>
        )}

        {/* Expandable Reasoning: "Show how I found this" */}
        {!msg.isStreaming && msg.text && (
          <details className="glean-reasoning-details">
            <summary className="glean-reasoning-summary">
              <span className="glean-chevron">⌄</span> Show how I found this
            </summary>
            <div className="glean-reasoning-body">
              <ul className="glean-reasoning-steps">
                {sourceInfo.steps.map((step, idx) => (
                  <li key={idx}>
                    <span className="glean-check-icon">✓</span>
                    <span>{step}</span>
                  </li>
                ))}
              </ul>

              {msg.sqlQuery && (
                <details className="glean-sql-box">
                  <summary className="glean-sql-summary">View SQL</summary>
                  <pre className="glean-sql-pre"><code>{msg.sqlQuery}</code></pre>
                </details>
              )}

              {msg.sources && msg.sources.length > 0 && (
                <div className="glean-source-citations">
                  <span className="citation-label">Referenced Policy Documents:</span>
                  <div className="citation-chips">
                    {msg.sources.map((s, idx) => (
                      <span key={idx} className="citation-chip">
                        📄 {s.title} ({s.category || 'Policy'})
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </details>
        )}
      </div>
    </div>
  )
}

function renderMessageText(text) {
  if (!text) return null
  // Simple inline markdown: **bold**, `code`, newlines
  const lines = text.split('\n')
  return lines.map((line, i) => (
    <span key={i}>
      {formatInline(line)}
      {i < lines.length - 1 && <br />}
    </span>
  ))
}

function formatInline(line) {
  // Bold: **text**
  const parts = line.split(/(\*\*[^*]+\*\*|`[^`]+`)/)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**'))
      return <strong key={i}>{part.slice(2, -2)}</strong>
    if (part.startsWith('`') && part.endsWith('`'))
      return <code key={i}>{part.slice(1, -1)}</code>
    return part
  })
}
