import type { Wallbox } from '@/shared/api/contracts/charging'
export type MicrogridSite = {
  config: {
    site_id: string
    site_name: string
    site_timezone: string
    source_timestamp_timezone: string
    source_timezone_evidence: string
    default_replay_at: string
    islanded: boolean
    assets: {
      id: string
      name: string
      kind: 'solar' | 'battery' | 'bus' | 'other'
      connected_to: string | null
    }[]
    battery_capacity_kwh: number
    battery_max_power_kw: number
    battery_min_soc_pct: number
    battery_model_efficiency: number
    battery_model_efficiency_note: string
    optimizer_min_coverage_pct: number
    optimizer_step_minutes: number
    optimizer_unserved_weight: number
    optimizer_curtailment_weight: number
    optimizer_throughput_weight: number
    battery_low_soc_alarm_pct: number
    battery_high_temp_alarm_c: number
    live_source: object | null
    control_integration: object | null
  }
  wallboxes: Pick<Wallbox, 'id' | 'vendor' | 'model' | 'firmware'>[]
  metadata: Record<string, string>
  default_raw: string
  mode: string
  live_connected: boolean
}
