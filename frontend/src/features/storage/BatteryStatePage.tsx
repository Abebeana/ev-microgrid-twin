import { formatPercent } from '@/shared/format/measurements'

import { useReplay } from '@/shared/state/replay-context'

import { BatteryPhysicsPanel } from '@/features/storage/BatteryPhysicsPanel'
import { SiteSummaryMetrics } from '@/features/telemetry/SiteSummaryMetrics'
import { TrendRangeControl } from '@/features/telemetry/TrendRangeControl'
import { DataPanel } from '@/shared/components/DataPanel'
import { DetailList } from '@/shared/components/DetailList'

import { TelemetryTrendChart } from '@/shared/charts/TelemetryTrendChart'

export function BatteryStatePage() {
  const { snapshot, site, rawTime } = useReplay()
  return (
    <>
      <SiteSummaryMetrics />
      <div className="content-grid">
        <DataPanel title="State of charge" className="wide" action={<TrendRangeControl />}>
          <TelemetryTrendChart series={['battery_soc_pct']} height={340} />
        </DataPanel>
        <DataPanel title="Storage">
          <DetailList
            rows={[
              { label: 'SoC', value: formatPercent(snapshot.battery_soc_pct) },
              {
                label: 'Temperature',
                value:
                  snapshot.battery_temp_c == null
                    ? '—'
                    : `${snapshot.battery_temp_c.toFixed(1)} °C`,
              },
              {
                label: 'Capacity',
                value: `${site.config.battery_capacity_kwh} kWh`,
              },
              {
                label: 'Inverter max',
                value: `${site.config.battery_max_power_kw} kW`,
              },
              {
                label: 'Reserve',
                value: `${site.config.battery_min_soc_pct}%`,
              },
            ]}
          />
        </DataPanel>
        <BatteryPhysicsPanel rawTime={rawTime} />
      </div>
    </>
  )
}
