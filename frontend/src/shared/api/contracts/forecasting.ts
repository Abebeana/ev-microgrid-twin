export type BaselineForecast = {
  model: string
  mode: string
  origin_raw: string
  origin_site_time: string
  source_sha256: string
  wallboxes_required: number
  scope: string
  uncertainty_note: string
  rows: {
    horizon_minutes: number
    raw_time: string
    site_time: string
    solar: {
      predicted_kw: number | null
      recorded_kw: number | null
      validation: {
        samples: number
        mae_kw: number | null
        p80_absolute_error_kw: number | null
      }
    }
    observed_ev: {
      predicted_kw: number | null
      recorded_kw: number | null
      validation: {
        samples: number
        mae_kw: number | null
        p80_absolute_error_kw: number | null
      }
    }
  }[]
}
