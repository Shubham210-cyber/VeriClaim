import type { Policy } from './types'

export const EVENT_OPTIONS: [string, string][] = [
  ['HARDWARE_FAILURE', 'Stopped working (hardware fault)'],
  ['MANUFACTURING_DEFECT', 'Defect since purchase'],
  ['ACCIDENTAL_DAMAGE', 'Accidental damage (drop, crack, impact)'],
  ['LIQUID_DAMAGE', 'Liquid spill or water damage'],
  ['THEFT', 'Theft or loss'],
  ['COSMETIC_WEAR', 'Cosmetic wear and tear'],
  ['OTHER', 'Something else / not sure'],
]
export const eventLabel = (v: string | null) => EVENT_OPTIONS.find(([k]) => k === v)?.[1] ?? '—'

export interface DocSlot { type: string; title: string; hint: string; required: boolean }

/** Which documents to ask for, derived from the cover (no backend change needed). */
export function documentSlots(policy: Policy | undefined, repairDone: boolean): DocSlot[] {
  const slots: DocSlot[] = []
  const req = new Set(policy?.required_evidence_types ?? ['PURCHASE_INVOICE'])
  if (req.has('PURCHASE_INVOICE') || !policy) {
    slots.push({ type: 'PURCHASE_INVOICE', title: 'Purchase invoice', required: true,
      hint: 'Must show the product model, serial number / IMEI and the purchase date.' })
  }
  if (policy?.requires_repair_receipt_if_repaired && repairDone) {
    slots.push({ type: 'REPAIR_RECEIPT', title: 'Repair receipt', required: true, hint: 'The service centre receipt for the repair already done.' })
  } else {
    slots.push({ type: 'REPAIR_RECEIPT', title: 'Repair receipt', required: false, hint: 'Only if a repair has already been carried out.' })
  }
  slots.push({ type: 'CUSTOMER_STATEMENT', title: "Customer's statement", required: false, hint: 'A short written account of what happened (text file or scan).' })
  slots.push({ type: 'OTHER', title: 'Other supporting document', required: false, hint: 'Anything else that helps, such as a photo of the damage.' })
  return slots
}

export const ACCEPT = '.pdf,.png,.jpg,.jpeg,.txt'
