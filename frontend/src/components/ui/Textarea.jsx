import React, { useId } from 'react'

/**
 * Textarea — labelled multi-line field.
 */
export default function Textarea({ label, id, hint, className = '', containerClassName = '', ...props }) {
  const autoId = useId()
  const areaId = id || autoId
  return (
    <div className={containerClassName}>
      {label && (
        <label htmlFor={areaId} className="mb-1 block text-xs font-medium text-secondary">
          {label}
        </label>
      )}
      <textarea
        id={areaId}
        className={`w-full rounded-md border border-default bg-surface px-3 py-2 text-sm text-primary
          placeholder:text-muted transition-colors resize-y
          focus:border-brand focus:outline-none focus-visible:outline-none
          disabled:bg-subtle disabled:text-secondary ${className}`}
        {...props}
      />
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </div>
  )
}
