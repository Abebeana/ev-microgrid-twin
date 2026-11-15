import type { ReactNode } from 'react'

import { CircleQuestionMark } from 'lucide-react'

export function UnavailableState({
  title,
  reason,
  action,
}: {
  title: string
  reason: string
  action?: ReactNode
}) {
  return (
    <div className="unavailable">
      <span className="unavailable-mark" aria-hidden="true">
        <CircleQuestionMark size={19} />
      </span>
      <h3>{title}</h3>
      <p>{reason}</p>
      {action}
    </div>
  )
}
