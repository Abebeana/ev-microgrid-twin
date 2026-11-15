export type PhysicalForecast = {
  model: string
  calibrated: boolean
  confidence_level: number | null
  scale_on_one_kw_array: number | null
  training_samples: number
  nameplate_clip_kw: number
  location_assumption: string
  pv_nameplate_note: string
  origin_site_time: string
  rows: {
    horizon_minutes: number
    site_time: string
    clearsky_kw: number
    lower_kw: number | null
    upper_kw: number | null
    recorded_kw: number | null
  }[]
}

export type PowerFlow = {
  converged: boolean
  reason?: string
  inverter_kw?: number
  inverter_kvar?: number
  minimum_voltage_pu?: number
  maximum_feeder_loading_pct?: number
  losses_kw?: number
  solar_measured?: boolean
  charging_kw?: number
  unmeasured_chargers?: string[]
  forming_source?: string
  buses?: { name: string; voltage_pu: number; angle_deg: number }[]
  feeders?: { name: string; loading_pct: number; current_a: number; power_kw: number }[]
  assumptions?: { note: string }
}

export type BatteryModel = {
  model: string
  direction: string
  minutes: number
  pack_power_kw: number
  ending_soc_pct: number
  cell_voltage_v: number
  pack_voltage_v: number
  cell_temperature_c: number
  series_cells: number
  parallel_cells: number
  modeled_pack_kwh: number
  assumption: string
  solar_measured: boolean
  charging_measured: boolean
}

export type OcppRegistry = {
  protocol: string
  socket: string
  charge_points: {
    charge_point_id: string
    vendor: string | null
    model: string | null
    status: string
    connected: boolean
    transaction_id: number | null
    power_kw: number | null
    meter_wh: number | null
  }[]
}
