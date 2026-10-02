import React from 'react'
import { ProvenanceBadge } from './ProvenanceBadge'
import { cn } from '../../lib/utils'

/**
 * SectionCard — renders one Master Claim Form section (design §13.2).
 *
 * `fields` is a list of { key, label, prov } where `prov` is a canonical
 * FieldProvenance object { field, value, source_document, page, confidence,
 * status, conflicts, note }. Each scalar shows its value, a status badge, and
 * its source_document + page. CONFLICT fields expand to every conflicts[]
 * value with its own source. Missing and conflicting fields are shown, never
 * hidden.
 *
 * `onFieldClick(prov)` (optional) lets a parent jump to the field's source
 * page in the document viewer.
 */
function humanize(key) {
  return String(key)
    .replace(/_/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/^./, (c) => c.toUpperCase())
}

function displayValue(value) {
  if (value === null || value === undefined || value === '') return '—'
  if (Array.isArray(value)) return value.length ? value.join(', ') : '—'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function sourceLine(prov) {
  const src = prov?.source_document
  const page = prov?.page
  if (!src && (page === null || page === undefined)) return null
  return [src || 'unknown source', page != null ? `p.${page}` : null].filter(Boolean).join(' · ')
}

export function SectionCard({ title, fields = [], onFieldClick, children }) {
  const rows = fields.filter((f) => f && f.prov)
  return (
    <section className="panel overflow-hidden" aria-label={title}>
      <header className="border-b border-border px-4 py-3">
        <h3 className="text-[14px] font-semibold text-foreground">{title}</h3>
      </header>
      {rows.length > 0 && (
        <dl className="divide-y divide-border">
          {rows.map(({ key, label, prov }) => {
            const src = sourceLine(prov)
            const clickable = typeof onFieldClick === 'function' && prov.page != null
            const conflicts = Array.isArray(prov.conflicts) ? prov.conflicts : []
            return (
              <div key={key} className="px-4 py-2.5">
                <div className="flex items-start justify-between gap-3">
                  <dt className="text-[12.5px] text-muted-foreground">{label || humanize(key)}</dt>
                  <dd className="flex min-w-0 flex-col items-end gap-1 text-right">
                    <button
                      type="button"
                      disabled={!clickable}
                      onClick={clickable ? () => onFieldClick(prov) : undefined}
                      className={cn(
                        'break-words text-[13px] font-medium text-foreground',
                        clickable && 'underline decoration-dotted underline-offset-2 hover:text-primary',
                      )}
                      title={clickable ? 'Jump to source page' : undefined}
                    >
                      {displayValue(prov.value)}
                    </button>
                    <div className="flex items-center gap-1.5">
                      <ProvenanceBadge status={prov.status} />
                      {typeof prov.confidence === 'number' && prov.confidence > 0 && (
                        <span className="text-[10px] tabular-nums text-subtle-foreground">
                          {Math.round(prov.confidence * 100)}%
                        </span>
                      )}
                    </div>
                  </dd>
                </div>
                {src && <p className="mt-1 text-[11px] text-subtle-foreground">{src}</p>}
                {conflicts.length > 0 && (
                  <ul className="mt-2 space-y-1 rounded-md border border-destructive/30 bg-destructive/5 p-2">
                    <li className="text-[10px] font-bold uppercase tracking-wide text-destructive">
                      Conflicting values
                    </li>
                    {conflicts.map((c, i) => (
                      <li key={i} className="flex items-center justify-between gap-3 text-[12px]">
                        <span className="font-medium text-foreground">{displayValue(c.value)}</span>
                        <span className="text-[11px] text-subtle-foreground">
                          {[c.source_document || 'unknown source', c.page != null ? `p.${c.page}` : null]
                            .filter(Boolean)
                            .join(' · ')}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )
          })}
        </dl>
      )}
      {children}
    </section>
  )
}
