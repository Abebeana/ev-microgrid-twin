export type DispatchPolicyMethod = 'idle' | 'greedy' | 'rl' | 'oracle'

export type PolicyEnergyTotals = {
  unserved_ev_kwh: number
  curtailed_pv_kwh: number
  battery_throughput_kwh: number
}

export type PolicyEvaluationReport = {
  mode: 'simulated_current_replay'
  advisory_only: true
  scope: string
  clock_note: string
  run_hash: string
  source: {
    sha256: string
    site_config_sha256: string
    first: string
    last: string
    timezone_interpretation: string
    test_first: string
    test_last: string
    test_days: number
    simulated_current_at: string
    simulated_shift_seconds: number
  }
  experiment: {
    algorithm: string
    policy_sha256: string
    seed: number
    training_iterations: number
    training_episodes: number
    training_steps: number
    test_episodes: number
    test_steps: number
    excluded_low_coverage_slots: number
    rl_greedy_fallback_steps: number
    minimum_coverage_pct: number
    minimum_episode_steps: number
    battery_capacity_kwh: number
    battery_max_power_kw: number
    battery_min_soc_pct: number
    assumed_round_trip_efficiency: number
    comparison_note: string
  }
  totals: Record<DispatchPolicyMethod, PolicyEnergyTotals>
  daily: {
    source_day: string
    methods: Record<DispatchPolicyMethod, PolicyEnergyTotals>
  }[]
  points: {
    source_time: string
    simulated_at: string
    solar_kw: number
    observed_ev_kw: number
    pv_minutes: number
    ev_minutes: number
    minimum_reporting_wallboxes: number
    measured_start_soc_pct: number | null
    outcomes: Record<
      DispatchPolicyMethod,
      {
        battery_kw: number
        unserved_ev_kwh: number
        curtailed_pv_kwh: number
        ending_soc_pct: number
      }
    >
  }[]
}
