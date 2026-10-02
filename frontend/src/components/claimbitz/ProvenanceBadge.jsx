import React from 'react'
import { cn } from '../../lib/utils'

/**
 * ProvenanceBadge — the canonical FieldProvenance status badge.
 *
 * Renders the backend `status` (EXTRACTED / MISSING / CONFLICT / VERIFIED /
 * LOW_CONFIDENCE) as a readable, color-coded chip. Missing and conflicting
 * statuses are shown, never hidden (design §13.2).
 */
const STATUS_META = {
  EXTRACTED: { label: 'Extracted', cls: 'bg-success-subtle text-success' },
  VERIFIED: { label: 'Verified', cls: 'bg-success-subtle text-success' },
  MISSING: { label: 'Missing', cls: 'bg-surface-muted text-subtle-foreground' },
  CONFLICT: { label: 'Conflict', cls: 'bg-destructive/10 text-destructive' },
  LOW_CONFIDENCE: { label: 'Low Confidence', cls: 'bg-warning-subtle text-warning' },
}

export function ProvenanceBadge({ status, className }) {
  const key = String(status || 'MISSING').toUpperCase()
  const meta = STATUS_META[key] || { label: key, cls: 'bg-surface-muted text-muted-foreground' }
  return (
    <span
      data-status={key}
      className={cn(
        'inline-flex items-center whitespace-nowrap rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide',
        meta.cls,
        className,
      )}
    >
      {meta.label}
    </span>
  )
}

export { STATUS_META }
