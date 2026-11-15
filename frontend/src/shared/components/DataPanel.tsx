import type { ReactNode } from 'react'

import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card'

export function DataPanel({
  title,
  eyebrow,
  action,
  children,
  className = '',
}: {
  title: string
  eyebrow?: string
  action?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <Card className={`panel gap-0 rounded-none py-0 shadow-none ${className}`}>
      <CardHeader className="panel-head">
        <div>
          {eyebrow && <span className="panel-eyebrow">{eyebrow}</span>}
          <CardTitle>{title}</CardTitle>
        </div>
        {action}
      </CardHeader>
      <CardContent className="panel-body">{children}</CardContent>
    </Card>
  )
}
