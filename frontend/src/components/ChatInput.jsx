import { useRef, useState } from 'react'
import './ChatInput.css'

/**
 * ChatInput — message text area with send button
 *
 * Props:
 *   onSend(message: string) — called when user submits
 *   disabled                 — while streaming
 */
export default function ChatInput({ onSend, disabled }) {
  const [text, setText] = useState('')
  const textareaRef = useRef(null)

  function submit() {
    const msg = text.trim()
    if (!msg || disabled) return
    onSend(msg)
    setText('')
    textareaRef.current?.focus()
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  function handleInput(e) {
    setText(e.target.value)
    // Auto-grow textarea
    const ta = textareaRef.current
    if (ta) {
      ta.style.height = 'auto'
      ta.style.height = Math.min(ta.scrollHeight, 160) + 'px'
    }
  }

  const charCount = text.length
  const nearLimit = charCount > 900

  return (
    <div className="chat-input-wrap">
      <div className={`chat-input-box glass ${disabled ? 'chat-input-box--disabled' : ''}`}>
        <textarea
          ref={textareaRef}
          id="chat-textarea"
          className="chat-textarea"
          placeholder="Ask about HR policies, query data, or request an action… (Enter to send)"
          value={text}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={1}
          maxLength={1000}
          aria-label="Message input"
        />
        <div className="chat-input-actions">
          {nearLimit && (
            <span className="char-count" aria-live="polite">
              {charCount}/1000
            </span>
          )}
          <button
            id="chat-send-btn"
            type="button"
            className="chat-send-btn btn btn-primary"
            onClick={submit}
            disabled={disabled || !text.trim()}
            aria-label="Send message"
            title="Send (Enter)"
          >
            {disabled
              ? <span className="spinner" />
              : <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            }
          </button>
        </div>
      </div>
      <p className="chat-input-hint">
        Shift + Enter for new line &middot; The AI router picks the right agent automatically
      </p>
    </div>
  )
}
