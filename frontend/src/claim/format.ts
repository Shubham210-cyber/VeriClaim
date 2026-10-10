import { fmtDay, money } from '../api'
import type { Fact } from '../types'

const DATE_FIELDS = ['purchase_date', 'incident_date', 'repair_date']
const MONEY_FIELDS = ['purchase_amount', 'repair_amount', 'claimed_amount']

/** Human-readable form of an extracted fact, or null when the value could not be understood. */
export const pretty = (f: Fact) => {
  if (f.normalized_value === null) return null
  if (DATE_FIELDS.includes(f.field_name)) return fmtDay(f.normalized_value)
  if (MONEY_FIELDS.includes(f.field_name)) return money(f.normalized_value)
  return f.normalized_value
}
