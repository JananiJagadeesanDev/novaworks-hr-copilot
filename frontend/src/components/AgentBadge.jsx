/**
 * AgentBadge — shows which AI agent handled a message
 */
const AGENT_META = {
  policy_rag:   { label: 'Policy RAG',   cls: 'tag-policy', icon: '📋' },
  sql_agent:    { label: 'SQL Agent',    cls: 'tag-sql',    icon: '🔍' },
  action_agent: { label: 'Action Agent', cls: 'tag-action', icon: '⚙️' },
  none:         { label: 'Copilot',      cls: 'tag-router', icon: '🤖' },
}

export default function AgentBadge({ agent }) {
  const meta = AGENT_META[agent] || AGENT_META['none']
  return (
    <span className={`tag ${meta.cls}`} title={`Handled by ${meta.label}`}>
      {meta.icon} {meta.label}
    </span>
  )
}
