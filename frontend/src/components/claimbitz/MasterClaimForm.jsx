import React from 'react'
import { FlaskConical } from 'lucide-react'
import { SectionCard } from './SectionCard'
import { ProvenanceBadge } from './ProvenanceBadge'
import { SYNTHETIC_DEMO_LABEL } from '../../hooks/useClaimAgent'
import { cn } from '../../lib/utils'

/**
 * MasterClaimForm — renders the canonical `masterClaimForm` object returned by
 * /process across all 12 sections (design §13.2). Every scalar carries a
 * provenance badge, source and page; MISSING and CONFLICT fields are shown,
 * never hidden. The list sections (procedures / investigations / medications /
 * billing) render as tables with per-cell badges, and billing shows the
 * calculated / submitted totals, the difference and the flag.
 *
 * `demoMode` adds the SYNTHETIC DEMO banner (design §13.4).
 * `onFieldClick(prov)` jumps to a field's source page in the document viewer.
 */

// Dotted layout of scalar fields per section, in display order.
const SCALAR_SECTIONS = [
  { key: 'claim_info', title: 'Claim Info', fields: ['claim_id', 'claim_type', 'submission_date', 'status', 'extraction_confidence'] },
  { key: 'patient', title: 'Patient', fields: ['name', 'dob', 'age', 'gender', 'patient_id', 'address', 'phone', 'email', 'blood_group', 'insurance_id'] },
  { key: 'policy', title: 'Policy', fields: ['insurer_name', 'policy_number', 'policyholder_name', 'start_date', 'end_date', 'plan_name', 'coverage_type', 'sum_insured', 'remaining_sum_insured', 'room_rent_limit', 'copay', 'deductible', 'waiting_period', 'exclusions', 'policy_status'] },
  { key: 'provider', title: 'Provider', fields: ['hospital_name', 'address', 'registration_number', 'provider_id', 'npi', 'doctor_name', 'doctor_registration_number', 'specialization', 'department'] },
  { key: 'hospitalization', title: 'Hospitalization', fields: ['admission_date', 'admission_time', 'discharge_date', 'discharge_time', 'admission_type', 'ward', 'bed', 'icu_stay', 'length_of_stay'] },
  { key: 'clinical', title: 'Clinical', fields: ['chief_complaint', 'symptoms', 'findings', 'primary_diagnosis', 'secondary_diagnoses', 'diagnosis_codes', 'history', 'allergies'] },
]

// List sections: table columns map to each line item's FieldProvenance keys.
const LIST_SECTIONS = [
  { key: 'procedures', title: 'Procedures', columns: ['name', 'code', 'date', 'description', 'doctor', 'amount'] },
  { key: 'investigations', title: 'Investigations', columns: ['name', 'date', 'result', 'reference_range', 'amount'] },
  { key: 'medications', title: 'Medications', columns: ['name', 'dosage', 'frequency', 'route', 'start_date', 'end_date', 'amount'] },
]

function humanize(key) {
  return String(key)
    .replace(/_/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/^./, (c) => c.toUpperCase())
}

function cellValue(value) {
  if (value === null || value === undefined || value === '') return '—'
  if (Array.isArray(value)) return value.length ? value.join(', ') : '—'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function toScalarFields(section, keys) {
  if (!section) return []
  return keys
    .filter((k) => section[k] && typeof section[k] === 'object' && 'status' in section[k])
    .map((k) => ({ key: k, label: humanize(k), prov: section[k] }))
}

function ListTable({ title, columns, section, onFieldClick }) {
  const items = Array.isArray(section?.items) ? section.items : []
  const listStatus = section?.list_status || 'MISSING'
  return (
    <SectionCard title={title}>
      <div className="flex items-center gap-2 px-4 py-2 text-[11px] text-subtle-foreground">
        <span>List status</span>
        <ProvenanceBadge status={listStatus} />
        <span className="tabular-nums">{items.length} item{items.length === 1 ? '' : 's'}</span>
      </div>
      {items.length > 0 ? (
        <div className="overflow-x-auto border-t border-border">
          <table className="w-full text-left text-[12px]">
            <thead>
              <tr className="bg-surface-muted">
                {columns.map((c) => (
                  <th key={c} className="whitespace-nowrap px-3 py-2 font-semibold text-muted-foreground">
                    {humanize(c)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {items.map((item, ri) => (
                <tr key={ri}>
                  {columns.map((c) => {
                    const prov = item?.[c]
                    const hasProv = prov && typeof prov === 'object' && 'status' in prov
                    const clickable = hasProv && typeof onFieldClick === 'function' && prov.page != null
                    return (
                      <td key={c} className="px-3 py-2 align-top">
                        <button
                          type="button"
                          disabled={!clickable}
                          onClick={clickable ? () => onFieldClick(prov) : undefined}
                          className={cn(
                            'block max-w-[220px] break-words text-left font-medium text-foreground',
                            clickable && 'underline decoration-dotted underline-offset-2 hover:text-primary',
                          )}
                        >
                          {cellValue(hasProv ? prov.value : prov)}
                        </button>
                        {hasProv && (
                          <div className="mt-1">
                            <ProvenanceBadge status={prov.status} />
                          </div>
                        )}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="border-t border-border px-4 py-3 text-[12px] text-subtle-foreground">
          No {title.toLowerCase()} extracted.
        </p>
      )}
    </SectionCard>
  )
}

function BillingSection({ billing, onFieldClick }) {
  if (!billing) return null
  const lines = Array.isArray(billing.line_items) ? billing.line_items : []
  const flag = billing.flag || 'INSUFFICIENT_DATA'
  const consistent = flag === 'BILLING_TOTAL_CONSISTENT'
  const fmt = (p) => (p && typeof p === 'object' && 'value' in p ? p : { value: p })
  const calc = fmt(billing.calculated_total)
  const submitted = fmt(billing.submitted_total)
  const diff = fmt(billing.billing_difference)
  const currency = fmt(billing.currency)
  const num = (v) => (v === null || v === undefined ? '—' : v)

  return (
    <SectionCard title="Billing">
      {lines.length > 0 ? (
        <div className="overflow-x-auto border-b border-border">
          <table className="w-full text-left text-[12px]">
            <thead>
              <tr className="bg-surface-muted">
                {['category', 'description', 'amount'].map((c) => (
                  <th key={c} className="whitespace-nowrap px-3 py-2 font-semibold text-muted-foreground">{humanize(c)}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {lines.map((line, ri) => (
                <tr key={ri}>
                  {['category', 'description', 'amount'].map((c) => {
                    const prov = line?.[c]
                    const hasProv = prov && typeof prov === 'object' && 'status' in prov
                    return (
                      <td key={c} className="px-3 py-2 align-top">
                        <span className="font-medium text-foreground">{cellValue(hasProv ? prov.value : prov)}</span>
                        {hasProv && <div className="mt-1"><ProvenanceBadge status={prov.status} /></div>}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="border-b border-border px-4 py-3 text-[12px] text-subtle-foreground">No billing lines extracted.</p>
      )}

      <dl className="divide-y divide-border">
        <div className="flex items-center justify-between gap-3 px-4 py-2.5">
          <dt className="text-[12.5px] text-muted-foreground">Calculated total</dt>
          <dd className="text-[13px] font-semibold tabular-nums text-foreground">{num(calc.value)}</dd>
        </div>
        <div className="flex items-center justify-between gap-3 px-4 py-2.5">
          <dt className="text-[12.5px] text-muted-foreground">Submitted total</dt>
          <dd className="flex items-center gap-2 text-[13px] font-semibold tabular-nums text-foreground">
            {num(submitted.value)}
            {submitted.status && <ProvenanceBadge status={submitted.status} />}
          </dd>
        </div>
        <div className="flex items-center justify-between gap-3 px-4 py-2.5">
          <dt className="text-[12.5px] text-muted-foreground">Billing difference</dt>
          <dd className="text-[13px] font-semibold tabular-nums text-foreground">{num(diff.value)}</dd>
        </div>
        {currency.value && (
          <div className="flex items-center justify-between gap-3 px-4 py-2.5">
            <dt className="text-[12.5px] text-muted-foreground">Currency</dt>
            <dd className="text-[13px] font-medium text-foreground">{currency.value}</dd>
          </div>
        )}
        <div className="flex items-center justify-between gap-3 px-4 py-2.5">
          <dt className="text-[12.5px] text-muted-foreground">Flag</dt>
          <dd>
            <span
              className={cn(
                'rounded px-2 py-0.5 text-[11px] font-bold uppercase tracking-wide',
                consistent ? 'bg-success-subtle text-success' : 'bg-warning-subtle text-warning',
              )}
            >
              {humanize(flag)}
            </span>
          </dd>
        </div>
      </dl>
    </SectionCard>
  )
}

function SupportingDocuments({ docs }) {
  if (!docs) return null
  const entries = Object.entries(docs).filter(([, v]) => v && typeof v === 'object' && 'present' in v)
  return (
    <SectionCard title="Supporting Documents">
      <ul className="divide-y divide-border">
        {entries.map(([key, doc]) => (
          <li key={key} className="flex items-center justify-between gap-3 px-4 py-2.5">
            <span className="text-[12.5px] text-muted-foreground">{humanize(key)}</span>
            <span className="flex items-center gap-2">
              <span className={cn('text-[12px] font-medium', doc.present ? 'text-success' : 'text-subtle-foreground')}>
                {doc.present ? 'Present' : 'Not included'}
              </span>
              <ProvenanceBadge status={doc.status} />
            </span>
          </li>
        ))}
      </ul>
    </SectionCard>
  )
}

function JurisdictionSection({ jurisdiction }) {
  if (!jurisdiction) return null
  const rows = [
    ['Jurisdiction', jurisdiction.jurisdiction],
    ['Currency', jurisdiction.currency],
    ['NPI required', String(!!jurisdiction.npi_required)],
    ['Procedure coding required', String(!!jurisdiction.procedure_coding_required)],
    ['Provider registration expected', String(!!jurisdiction.provider_registration_expected)],
    ['Inferred from', jurisdiction.inferred_from],
  ]
  return (
    <SectionCard title="Jurisdiction">
      <dl className="divide-y divide-border">
        {rows.map(([label, value]) => (
          <div key={label} className="flex items-center justify-between gap-3 px-4 py-2.5">
            <dt className="text-[12.5px] text-muted-foreground">{label}</dt>
            <dd className="text-[13px] font-medium text-foreground">{value || '—'}</dd>
          </div>
        ))}
      </dl>
    </SectionCard>
  )
}

export function MasterClaimForm({ masterClaimForm, demoMode = false, onFieldClick }) {
  if (!masterClaimForm || typeof masterClaimForm !== 'object') {
    return (
      <section className="panel px-5 py-6 text-center text-[13px] text-muted-foreground">
        No Master Claim Form available for this claim.
      </section>
    )
  }
  const form = masterClaimForm

  return (
    <div className="space-y-4" aria-label="Master Claim Form">
      {demoMode && (
        <div
          data-testid="synthetic-demo-banner"
          className="flex items-center gap-2 rounded-md border border-dashed border-warning/40 bg-warning/5 px-4 py-2 text-[12px] font-semibold uppercase tracking-wide text-warning"
        >
          <FlaskConical className="h-3.5 w-3.5" aria-hidden />
          {SYNTHETIC_DEMO_LABEL} — this data is illustrative, not a real claim
        </div>
      )}

      <JurisdictionSection jurisdiction={form.jurisdiction} />

      {SCALAR_SECTIONS.map(({ key, title, fields }) => (
        <SectionCard
          key={key}
          title={title}
          fields={toScalarFields(form[key], fields)}
          onFieldClick={onFieldClick}
        />
      ))}

      {LIST_SECTIONS.map(({ key, title, columns }) => (
        <ListTable key={key} title={title} columns={columns} section={form[key]} onFieldClick={onFieldClick} />
      ))}

      <BillingSection billing={form.billing} onFieldClick={onFieldClick} />
      <SupportingDocuments docs={form.supporting_documents} />
    </div>
  )
}
