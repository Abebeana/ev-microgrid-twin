export type Wallbox = {
  id: string
  vendor: string | null
  model: string | null
  firmware: string | null
  power_kw: number | null
  power_sample_count: number
  power_raw_time: string | null
  power_site_time: string | null
  status: string
  status_stale: boolean
  error_code: string | null
  status_site_time: string | null
}

export type Session = {
  transaction_id: number
  wallbox_id: string
  start_raw: string
  stop_raw: string | null
  start_site_time: string
  stop_site_time: string | null
  meter_delta_raw: number | null
  stop_reason: string | null
}
