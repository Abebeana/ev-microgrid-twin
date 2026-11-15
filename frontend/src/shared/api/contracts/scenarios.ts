export type ScenarioInput = {
  start: string
  hours: number
  charging_multiplier: number
  solar_multiplier: number
  battery_capacity_kwh: number | null
  outage_wallbox_id: string | null
}

export type ScenarioResult = {
  mode: string
  advisory_only: boolean
  scope: string
  initial_soc_pct: number
  run_hash: string
  schedule: {
    raw_time: string
    site_time: string
    solar_kw: number
    observed_charging_kw: number
    coverage_pct: number
    minimum_reporting_wallboxes: number
    battery_charge_kw: number
    battery_discharge_kw: number
    unserved_ev_kw: number
    curtailed_pv_kw: number
    ending_soc_pct: number
  }[]
  totals: {
    unserved_ev_kwh: number
    curtailed_pv_kwh: number
    battery_discharge_kwh: number
    baseline_without_dispatch_unserved_ev_kwh: number
  }
  provenance: Record<string, unknown>
}
