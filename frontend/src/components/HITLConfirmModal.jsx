import './HITLConfirmModal.css'

/**
 * HITLConfirmModal — Human-in-the-Loop confirmation dialog
 *
 * Props:
 *   message        — original user message
 *   pendingAction  — description of the action to confirm
 *   confirmationId — HITL ID from the backend
 *   onConfirm(confirmationId)  — user clicked Confirm
 *   onDeny()                   — user clicked Cancel
 *   loading                    — confirm API call in progress
 */
export default function HITLConfirmModal({
  message,
  pendingAction,
  confirmationId,
  onConfirm,
  onDeny,
  loading,
}) {
  return (
    <div className="hitl-overlay" role="dialog" aria-modal="true" aria-labelledby="hitl-title">
      <div className="hitl-card glass-bright fade-in">
        <div className="hitl-header">
          <span className="hitl-icon">⚠️</span>
          <div>
            <h3 id="hitl-title">Confirm High-Impact Action</h3>
            <p>This action requires your explicit approval before proceeding.</p>
          </div>
        </div>

        <div className="hitl-body">
          <div className="hitl-field">
            <span className="hitl-field-label">Your request</span>
            <blockquote className="hitl-quote">{message}</blockquote>
          </div>
          <div className="hitl-field">
            <span className="hitl-field-label">Action to perform</span>
            <div className="hitl-action-box">{pendingAction}</div>
          </div>
        </div>

        <div className="hitl-footer">
          <button
            id="hitl-deny-btn"
            type="button"
            className="btn btn-secondary"
            onClick={onDeny}
            disabled={loading}
          >
            Cancel
          </button>
          <button
            id="hitl-confirm-btn"
            type="button"
            className="btn btn-primary"
            onClick={() => onConfirm(confirmationId)}
            disabled={loading}
          >
            {loading ? <><span className="spinner" /> Confirming…</> : '✓ Confirm Action'}
          </button>
        </div>
      </div>
    </div>
  )
}
