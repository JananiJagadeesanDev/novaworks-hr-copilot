/**
 * StatusChip — animated SSE stage indicator
 * stage: 'intent_classification' | 'routing' | 'execution'
 */
const STAGE_META = {
  intent_classification: { icon: '✨', label: 'Understanding request…' },
  routing:               { icon: '🔀', label: 'Routing to agent…' },
  execution:             { icon: '⚙️', label: 'Processing…' },
}

import './StatusChip.css'

export default function StatusChip({ stage, agent }) {
  const meta = STAGE_META[stage] || { icon: '…', label: stage }
  const label = stage === 'routing' && agent
    ? `Routed → ${agent.replace('_', ' ')}`
    : meta.label

  return (
    <div className="status-chip fade-in">
      <span className="status-chip-icon pulse-dot-alt">{meta.icon}</span>
      <span className="status-chip-label">{label}</span>
    </div>
  )
}
