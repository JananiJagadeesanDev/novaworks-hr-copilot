import { useEffect, useRef } from 'react'
import AgentBadge from './AgentBadge'
import StatusChip from './StatusChip'
import './ChatWindow.css'

/**
 * ChatWindow — renders the message list
 *
 * messages: Array of {
 *   id, role: 'user'|'assistant',
 *   text, agent?, statusStages?, isStreaming?
 * }
 */
export default function ChatWindow({ messages }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (messages.length === 0) {
    return <EmptyState />
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

function EmptyState() {
  const suggestions = [
    'What is the maternity leave policy?',
    'How many employees are in Engineering?',
    'Approve Raj Kumar\'s leave request',
    'What is our WFH policy?',
  ]
  return (
    <div className="chat-empty fade-in">
      <div className="chat-empty-icon">⚡</div>
      <h2 className="chat-empty-title">
        How can I help you today?
      </h2>
      <p className="chat-empty-sub">
        Ask about HR policies, query data, or request an HR action.
        I'll route your request to the right agent automatically.
      </p>
      <div className="chat-suggestions">
        {suggestions.map((s, i) => (
          <div key={i} className="chat-suggestion-chip">{s}</div>
        ))}
      </div>
    </div>
  )
}

function MessageBubble({ msg }) {
  const isUser = msg.role === 'user'

  return (
    <div className={`message-row ${isUser ? 'message-row--user' : 'message-row--assistant'} fade-in`}>
      {!isUser && (
        <div className="message-avatar message-avatar--assistant" aria-hidden="true">
          ⚡
        </div>
      )}

      <div className="message-content">
        {/* SSE status chips */}
        {msg.statusStages && msg.statusStages.length > 0 && (
          <div className="message-status-chips">
            {msg.statusStages.map((s, i) => (
              <StatusChip key={i} stage={s.stage} agent={s.agent} />
            ))}
          </div>
        )}

        <div className={`message-bubble ${isUser ? 'bubble--user' : 'bubble--assistant'}`}>
          {msg.isStreaming && !msg.text ? (
            <div className="typing-dots" aria-label="AI is thinking">
              <span /><span /><span />
            </div>
          ) : (
            <div className="message-text">
              {renderMessageText(msg.text)}
            </div>
          )}

          {/* Streaming cursor */}
          {msg.isStreaming && msg.text && (
            <span className="stream-cursor" aria-hidden="true" />
          )}
        </div>

        {/* Agent badge + metadata */}
        {!isUser && !msg.isStreaming && msg.agent && (
          <div className="message-meta">
            <AgentBadge agent={msg.agent} />
            {msg.sqlQuery && (
              <details className="sql-details">
                <summary>View SQL</summary>
                <pre><code>{msg.sqlQuery}</code></pre>
              </details>
            )}
            {msg.sources && msg.sources.length > 0 && (
              <div className="message-sources">
                <span className="sources-label">Sources:</span>
                {msg.sources.map((s, i) => (
                  <span key={i} className="source-chip">{s.title}</span>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {isUser && (
        <div className="message-avatar message-avatar--user" aria-hidden="true">
          👤
        </div>
      )}
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
