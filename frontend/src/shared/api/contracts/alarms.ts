export type Alarm = {
  id: string
  asset_id: string
  severity: string
  message: string
  raw_time: string
  site_time: string
  provenance: string
  acknowledgement: {
    actor: string
    acknowledged_at: string
    note: string
  } | null
}
