import { formatPercent, formatPower } from '@/shared/format/measurements'

import { useReplay } from '@/shared/state/replay-context'

import { MetricStrip } from '@/shared/components/MetricStrip'

export function SiteSummaryMetrics() {
  const { snapshot, site } = useReplay()
  return (
    <MetricStrip
      items={[
        {
          label: 'Solar',
          value: formatPower(snapshot.solar_kw),
          caption: `${snapshot.solar_samples} samples`,
        },
        {
          label: 'EV load',
          value: formatPower(snapshot.observed_charging_kw),
          caption: `${snapshot.observed_wallboxes}/${snapshot.total_wallboxes} reporting`,
        },
        {
          label: 'Battery',
          value: formatPercent(snapshot.battery_soc_pct),
          caption: `${site.config.battery_capacity_kwh} kWh`,
        },
        { label: 'Sessions', value: String(snapshot.active_sessions) },
      ]}
    />
  )
}
